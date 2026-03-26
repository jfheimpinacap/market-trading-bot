from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.agents.models import AgentPipelineType, AgentStatus
from apps.agents.services.handoffs import create_handoff
from apps.learning_memory.services import run_learning_rebuild
from apps.markets.models import Market, MarketSourceType, MarketStatus
from apps.postmortem_demo.services import generate_trade_reviews
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.research_agent.models import ResearchCandidate
from apps.research_agent.services.scan import run_research_scan
from apps.risk_agent.services import run_risk_assessment, run_risk_sizing


@dataclass
class PipelineExecutionResult:
    status: str
    summary: str
    details: dict
    agent_runs_count: int
    handoffs_count: int


class PipelineExecutionError(Exception):
    pass


def _get_market_direction(system_probability: Decimal) -> str:
    return 'YES' if system_probability >= Decimal('0.5000') else 'NO'


def run_research_to_prediction(*, context, payload: dict) -> PipelineExecutionResult:
    scan_agent = context.agents_by_slug['scan_agent']
    research_agent = context.agents_by_slug['research_agent']
    prediction_agent = context.agents_by_slug['prediction_agent']
    risk_agent = context.agents_by_slug['risk_agent']

    run_scan = bool(payload.get('run_scan', False))
    if run_scan:
        scan_run = context.start_agent_run(agent=scan_agent)
        try:
            scan_output = run_research_scan(run_analysis=bool(payload.get('run_analysis', True)))
            context.finish_agent_run(
                scan_run,
                status=AgentStatus.SUCCESS,
                summary=f'Research scan run #{scan_output.id} generated {scan_output.candidates_generated} candidates.',
                details={'research_scan_run_id': scan_output.id, 'status': scan_output.status},
            )
        except Exception as exc:
            context.finish_agent_run(scan_run, status=AgentStatus.FAILED, summary=f'Scan agent failed: {exc}', details={'error': str(exc)})
            raise PipelineExecutionError(str(exc)) from exc

        create_handoff(
            from_agent_run=scan_run,
            to_agent_definition=research_agent,
            pipeline_run=context.pipeline_run,
            handoff_type='scan_to_research',
            payload_summary='Scan output available for research shortlist refresh.',
            payload_ref={'research_scan_run_id': scan_output.id},
        )
        context.handoffs_count += 1

    research_run = context.start_agent_run(agent=research_agent)
    candidate_limit = int(payload.get('candidate_limit', 10) or 10)
    candidates = list(
        ResearchCandidate.objects.select_related('market').order_by('-priority', '-updated_at')[:candidate_limit]
    )
    candidate_payload = [
        {
            'candidate_id': candidate.id,
            'market_id': candidate.market_id,
            'market_slug': candidate.market.slug,
            'market_title': candidate.market.title,
            'priority': str(candidate.priority),
            'short_thesis': candidate.short_thesis,
            'sentiment_direction': candidate.sentiment_direction,
        }
        for candidate in candidates
    ]
    context.finish_agent_run(
        research_run,
        status=AgentStatus.SUCCESS if candidates else AgentStatus.PARTIAL,
        summary=f'Research agent prepared {len(candidates)} candidates for prediction.',
        details={'candidates': candidate_payload},
    )

    create_handoff(
        from_agent_run=research_run,
        to_agent_definition=prediction_agent,
        pipeline_run=context.pipeline_run,
        handoff_type='research_to_prediction',
        payload_summary=f'{len(candidates)} candidates handed to prediction agent.',
        payload_ref={'candidate_ids': [item['candidate_id'] for item in candidate_payload]},
    )
    context.handoffs_count += 1

    prediction_run = context.start_agent_run(agent=prediction_agent)
    scores = []
    for item in candidate_payload:
        market = Market.objects.filter(id=item['market_id']).first()
        if market is None:
            continue
        scoring_result = score_market_prediction(market=market, triggered_by='agent_orchestrator')
        scores.append(
            {
                'prediction_score_id': scoring_result.score.id,
                'market_id': market.id,
                'market_slug': market.slug,
                'system_probability': str(scoring_result.score.system_probability),
                'market_probability': str(scoring_result.score.market_probability),
                'edge': str(scoring_result.score.edge),
                'confidence': str(scoring_result.score.confidence),
            }
        )

    prediction_status = AgentStatus.SUCCESS if scores else AgentStatus.PARTIAL
    context.finish_agent_run(
        prediction_run,
        status=prediction_status,
        summary=f'Prediction agent scored {len(scores)} markets.',
        details={'scores': scores},
    )

    create_handoff(
        from_agent_run=prediction_run,
        to_agent_definition=risk_agent,
        pipeline_run=context.pipeline_run,
        handoff_type='prediction_to_risk',
        payload_summary=f'{len(scores)} prediction outputs sent for risk assessment.',
        payload_ref={'score_count': len(scores)},
    )
    context.handoffs_count += 1

    risk_run = context.start_agent_run(agent=risk_agent)
    risk_outputs = []
    for score in scores:
        market = Market.objects.filter(id=score['market_id']).first()
        if market is None:
            continue
        assessment = run_risk_assessment(market=market)
        sizing = run_risk_sizing(risk_assessment=assessment, base_quantity=Decimal('3.0000'))
        risk_outputs.append({'market_id': market.id, 'risk_assessment_id': assessment.id, 'risk_level': assessment.risk_level, 'adjusted_quantity': str(sizing.adjusted_quantity)})

    context.finish_agent_run(
        risk_run,
        status=AgentStatus.SUCCESS if risk_outputs else AgentStatus.PARTIAL,
        summary=f'Risk agent assessed {len(risk_outputs)} opportunities.',
        details={'risk_outputs': risk_outputs},
    )

    status = AgentStatus.SUCCESS if risk_outputs else AgentStatus.PARTIAL
    return PipelineExecutionResult(
        status=status,
        summary=f'Research→Prediction→Risk pipeline finished with {len(risk_outputs)} risk outputs.',
        details={'candidate_count': len(candidate_payload), 'score_count': len(scores), 'risk_count': len(risk_outputs)},
        agent_runs_count=context.agent_runs_count,
        handoffs_count=context.handoffs_count,
    )


def run_postmortem_to_learning(*, context, payload: dict) -> PipelineExecutionResult:
    postmortem_agent = context.agents_by_slug['postmortem_agent']
    learning_agent = context.agents_by_slug['learning_agent']

    postmortem_run = context.start_agent_run(agent=postmortem_agent)
    review_limit = payload.get('review_limit')
    review_results = generate_trade_reviews(limit=int(review_limit) if review_limit else None, refresh_existing=True)
    review_ids = [result.review.id for result in review_results]
    context.finish_agent_run(
        postmortem_run,
        status=AgentStatus.SUCCESS,
        summary=f'Postmortem agent generated/refreshed {len(review_ids)} reviews.',
        details={'review_ids': review_ids},
    )

    create_handoff(
        from_agent_run=postmortem_run,
        to_agent_definition=learning_agent,
        pipeline_run=context.pipeline_run,
        handoff_type='postmortem_to_learning',
        payload_summary=f'{len(review_ids)} reviews available for learning rebuild.',
        payload_ref={'review_ids': review_ids[:50], 'review_count': len(review_ids)},
    )
    context.handoffs_count += 1

    learning_run = context.start_agent_run(agent=learning_agent)
    rebuild_run = run_learning_rebuild(triggered_from='automation')
    context.finish_agent_run(
        learning_run,
        status=rebuild_run.status,
        summary=rebuild_run.summary,
        details={'learning_rebuild_run_id': rebuild_run.id, 'details': rebuild_run.details},
    )

    return PipelineExecutionResult(
        status=AgentStatus.SUCCESS if rebuild_run.status != AgentStatus.FAILED else AgentStatus.FAILED,
        summary='Postmortem→Learning pipeline completed.',
        details={'review_count': len(review_ids), 'learning_rebuild_run_id': rebuild_run.id},
        agent_runs_count=context.agent_runs_count,
        handoffs_count=context.handoffs_count,
    )


def run_real_market_agent_cycle(*, context, payload: dict) -> PipelineExecutionResult:
    research_agent = context.agents_by_slug['research_agent']
    prediction_agent = context.agents_by_slug['prediction_agent']
    risk_agent = context.agents_by_slug['risk_agent']

    market_limit = int(payload.get('market_limit', 5) or 5)
    markets = list(
        Market.objects.filter(source_type=MarketSourceType.REAL_READ_ONLY, is_active=True, status=MarketStatus.OPEN)
        .select_related('provider')
        .order_by('-updated_at', '-id')[:market_limit]
    )

    research_run = context.start_agent_run(agent=research_agent)
    market_scope = [
        {'market_id': market.id, 'market_slug': market.slug, 'title': market.title, 'provider': market.provider.slug}
        for market in markets
    ]
    context.finish_agent_run(
        research_run,
        status=AgentStatus.SUCCESS if market_scope else AgentStatus.PARTIAL,
        summary=f'Research agent selected {len(market_scope)} real read-only markets.',
        details={'market_scope': market_scope},
    )

    create_handoff(
        from_agent_run=research_run,
        to_agent_definition=prediction_agent,
        pipeline_run=context.pipeline_run,
        handoff_type='research_to_prediction_real_scope',
        payload_summary=f'{len(market_scope)} real read-only markets sent to prediction.',
        payload_ref={'market_ids': [item['market_id'] for item in market_scope]},
    )
    context.handoffs_count += 1

    prediction_run = context.start_agent_run(agent=prediction_agent)
    scores = []
    for market in markets:
        result = score_market_prediction(market=market, triggered_by='agent_orchestrator_real_cycle')
        scores.append(
            {
                'market_id': market.id,
                'market_slug': market.slug,
                'prediction_score_id': result.score.id,
                'system_probability': str(result.score.system_probability),
                'edge': str(result.score.edge),
                'confidence': str(result.score.confidence),
            }
        )
    context.finish_agent_run(
        prediction_run,
        status=AgentStatus.SUCCESS if scores else AgentStatus.PARTIAL,
        summary=f'Prediction agent scored {len(scores)} real read-only markets.',
        details={'scores': scores},
    )

    create_handoff(
        from_agent_run=prediction_run,
        to_agent_definition=risk_agent,
        pipeline_run=context.pipeline_run,
        handoff_type='prediction_to_risk',
        payload_summary=f'{len(scores)} prediction outputs sent for risk assessment.',
        payload_ref={'score_count': len(scores)},
    )
    context.handoffs_count += 1

    risk_run = context.start_agent_run(agent=risk_agent)
    assessments = []
    for score in scores:
        market = Market.objects.filter(id=score['market_id']).first()
        if market is None:
            continue
        assessment = run_risk_assessment(
            market=market,
            metadata={'origin': 'real_market_agent_cycle', 'prediction_score_id': score['prediction_score_id']},
        )
        sizing = run_risk_sizing(
            risk_assessment=assessment,
            base_quantity=Decimal(str(payload.get('quantity', '1.0000'))),
            metadata={'origin': 'real_market_agent_cycle'},
        )
        assessments.append(
            {
                'risk_assessment_id': assessment.id,
                'market_id': market.id,
                'risk_level': assessment.risk_level,
                'adjusted_quantity': str(sizing.adjusted_quantity),
                'summary': assessment.narrative_risk_summary,
            }
        )

    risk_status = AgentStatus.SUCCESS if assessments else AgentStatus.PARTIAL
    context.finish_agent_run(
        risk_run,
        status=risk_status,
        summary=f'Risk agent produced {len(assessments)} structured paper/demo assessments + sizing.',
        details={'assessments': assessments},
    )

    status = AgentStatus.SUCCESS if assessments else AgentStatus.PARTIAL
    return PipelineExecutionResult(
        status=status,
        summary='Real-market agent cycle completed in paper/demo only mode.',
        details={'market_scope_count': len(market_scope), 'scores_count': len(scores), 'assessments_count': len(assessments)},
        agent_runs_count=context.agent_runs_count,
        handoffs_count=context.handoffs_count,
    )


def execute_pipeline(*, context, pipeline_type: str, payload: dict) -> PipelineExecutionResult:
    if pipeline_type == AgentPipelineType.RESEARCH_TO_PREDICTION:
        return run_research_to_prediction(context=context, payload=payload)
    if pipeline_type == AgentPipelineType.POSTMORTEM_TO_LEARNING:
        return run_postmortem_to_learning(context=context, payload=payload)
    if pipeline_type == AgentPipelineType.REAL_MARKET_AGENT_CYCLE:
        return run_real_market_agent_cycle(context=context, payload=payload)
    raise PipelineExecutionError(f'Unsupported pipeline type: {pipeline_type}')
