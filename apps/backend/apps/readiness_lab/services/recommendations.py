def build_recommendations(*, failed_gates: list[dict], warning_gates: list[dict]) -> list[str]:
    recommendations: list[str] = []
    for gate in failed_gates:
        gate_name = gate['gate']
        if gate_name == 'minimum_replay_runs':
            recommendations.append('Run more replay sessions before considering promotion.')
        elif gate_name == 'minimum_live_paper_runs':
            recommendations.append('Run more continuous demo/evaluation sessions in paper-only mode.')
        elif gate_name == 'minimum_favorable_review_rate':
            recommendations.append('Improve favorable review rate through tighter policy and proposal filtering.')
        elif gate_name == 'maximum_block_rate':
            recommendations.append('Reduce block rate by refining policy thresholds and risk filters.')
        elif gate_name == 'maximum_safety_event_rate':
            recommendations.append('Lower safety event rate and verify stability window before promotion.')
        elif gate_name == 'maximum_hard_stop_count':
            recommendations.append('Resolve hard-stop triggers before any readiness promotion.')
        elif gate_name == 'maximum_drawdown':
            recommendations.append('Reduce drawdown volatility and keep losses within profile thresholds.')
        elif gate_name == 'maximum_operator_intervention_rate':
            recommendations.append('Lower operator intervention dependency with safer autonomous behavior.')
        elif gate_name == 'minimum_real_market_ops_coverage':
            recommendations.append('Increase real read-only market coverage while keeping paper-only execution.')
        elif gate_name == 'minimum_experiment_comparison_consistency':
            recommendations.append('Improve replay/live consistency using additional experiment comparisons.')
        else:
            recommendations.append(f'Resolve gate failure: {gate_name}.')

    if warning_gates:
        recommendations.append('Continue in paper-only mode and monitor warning gates over more runs.')

    if not recommendations:
        recommendations.append('Readiness profile gates are currently satisfied. Continue monitoring in paper/demo mode.')
    return recommendations
