from apps.go_live_gate.models import CapitalFirewallRule

DEFAULT_FIREWALL_RULES = [
    {
        'code': 'NO_REAL_CREDENTIALS_ACCEPTED',
        'title': 'No live credentials accepted',
        'description': 'Go-live rehearsal mode rejects broker/exchange credentials in this phase.',
    },
    {
        'code': 'NO_LIVE_ROUTE_ALLOWED',
        'title': 'No live route allowed',
        'description': 'Any routing target must remain sandbox/paper; live route IDs are blocked.',
    },
    {
        'code': 'NO_SEND_ORDER_ACTION',
        'title': 'No send_order action possible',
        'description': 'Final send order action is deliberately disabled; only dry-run dispositions are stored.',
    },
    {
        'code': 'FUTURE_LIVE_ADAPTER_MUST_PASS_GATE',
        'title': 'Future live adapters must pass gate',
        'description': 'A future live adapter must present an explicit policy flag and approval proof to proceed.',
    },
]


def ensure_default_firewall_rules() -> list[CapitalFirewallRule]:
    rules: list[CapitalFirewallRule] = []
    for rule in DEFAULT_FIREWALL_RULES:
        obj, _ = CapitalFirewallRule.objects.get_or_create(
            code=rule['code'],
            defaults={
                'title': rule['title'],
                'description': rule['description'],
                'enabled': True,
                'block_live_transition': True,
            },
        )
        rules.append(obj)
    return rules


def evaluate_firewall() -> dict:
    rules = ensure_default_firewall_rules()
    active_blocking_rules = [rule.code for rule in rules if rule.enabled and rule.block_live_transition]
    return {
        'firewall_enabled': True,
        'live_transition_allowed': False,
        'blocked_by_firewall': True,
        'blocking_rule_codes': active_blocking_rules,
        'rules': [
            {
                'code': rule.code,
                'title': rule.title,
                'description': rule.description,
                'enabled': rule.enabled,
                'block_live_transition': rule.block_live_transition,
            }
            for rule in rules
        ],
    }
