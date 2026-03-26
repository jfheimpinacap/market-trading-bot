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
        'name': 'Learning Agent',
        'slug': 'learning_agent',
        'agent_type': 'learning',
        'description': 'Rebuilds learning memory adjustments from postmortem, evaluation, and safety history.',
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
