from apps.agents.models import AgentDefinition

DEFAULT_AGENT_DEFINITIONS = [
    {
        'name': 'Scan Agent',
        'slug': 'scan_agent',
        'agent_type': 'scan',
        'description': 'Collects narrative sources and candidate market context for downstream research.',
    },
    {
        'name': 'Research Agent',
        'slug': 'research_agent',
        'agent_type': 'research',
        'description': 'Builds narrative shortlist and market candidate context from existing research module outputs.',
    },
    {
        'name': 'Prediction Agent',
        'slug': 'prediction_agent',
        'agent_type': 'prediction',
        'description': 'Scores candidates using prediction agent models and produces probability/edge/confidence outputs.',
    },
    {
        'name': 'Risk Agent',
        'slug': 'risk_agent',
        'agent_type': 'risk',
        'description': 'Applies conservative risk assessment and sizing guidance in paper/demo mode.',
    },
    {
        'name': 'Postmortem Agent',
        'slug': 'postmortem_agent',
        'agent_type': 'postmortem',
        'description': 'Generates trade outcome reviews with structured lessons for learning loops.',
    },

    {
        'name': 'Postmortem Board Agent',
        'slug': 'postmortem_board_agent',
        'agent_type': 'postmortem_board',
        'description': 'Runs structured multi-perspective postmortem board review and outputs auditable board conclusions.',
    },
    {
        'name': 'Learning Agent',
        'slug': 'learning_agent',
        'agent_type': 'learning',
        'description': 'Rebuilds learning memory adjustments from postmortem, evaluation, and safety history.',
    },
    {
        'name': 'Opportunity Supervisor Agent',
        'slug': 'opportunity_supervisor_agent',
        'agent_type': 'opportunity_supervisor',
        'description': 'Runs end-to-end opportunity cycle from signal fusion to proposal/allocation execution path resolution.',
    },
    {
        'name': 'Position Manager Agent',
        'slug': 'position_manager_agent',
        'agent_type': 'position_manager',
        'description': 'Runs position lifecycle governance to decide hold/reduce/close/review for open paper positions.',
    },
]


def ensure_default_agent_definitions() -> list[AgentDefinition]:
    records: list[AgentDefinition] = []
    for payload in DEFAULT_AGENT_DEFINITIONS:
        record, _ = AgentDefinition.objects.get_or_create(
            slug=payload['slug'],
            defaults={
                **payload,
                'is_enabled': True,
                'input_schema_version': 'v1',
                'output_schema_version': 'v1',
            },
        )
        records.append(record)
    return records
