from apps.signals.models import MockAgent, MockAgentRoleType

MOCK_AGENTS = [
    {
        'name': 'Scan Agent',
        'slug': 'scan-agent',
        'role_type': MockAgentRoleType.SCAN,
        'description': 'Fast local scanner that flags markets with unusual moves, spread conditions, or notable status changes.',
        'notes': 'Demo-only agent. Uses deterministic local heuristics over seeded market fields and snapshots.',
    },
    {
        'name': 'Research Agent',
        'slug': 'research-agent',
        'role_type': MockAgentRoleType.RESEARCH,
        'description': 'Creates short thesis-style explanations for demo opportunities and notable market states.',
        'notes': 'No external research, LLM calls, or provider scraping are used in this stage.',
    },
    {
        'name': 'Prediction Agent',
        'slug': 'prediction-agent',
        'role_type': MockAgentRoleType.PREDICTION,
        'description': 'Compares current market probability against a simple local heuristic baseline.',
        'notes': 'This is not a real model. It only compares recent snapshots and simple bounded heuristics.',
    },
    {
        'name': 'Risk Agent',
        'slug': 'risk-agent',
        'role_type': MockAgentRoleType.RISK,
        'description': 'Marks signals as low-confidence or not actionable when market conditions are weak or terminal.',
        'notes': 'Focused on demo safety flags like paused, resolved, low activity, or wide spread.',
    },
    {
        'name': 'Postmortem Agent',
        'slug': 'postmortem-agent',
        'role_type': MockAgentRoleType.POSTMORTEM,
        'description': 'Reserved for future retrospective analysis of expired or resolved signals.',
        'notes': 'Included now so the signals layer already knows about future lifecycle roles.',
    },
]


def seed_mock_agents() -> dict[str, int]:
    created = 0
    updated = 0

    for payload in MOCK_AGENTS:
        _, was_created = MockAgent.objects.update_or_create(
            slug=payload['slug'],
            defaults={**payload, 'is_active': True},
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        'total': len(MOCK_AGENTS),
        'created': created,
        'updated': updated,
    }
