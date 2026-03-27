BASE_CASES: list[dict] = [
    {'code': 'basic_buy_yes_mapping', 'group': 'payload', 'description': 'Valid BUY market-like mapping should pass payload and dry-run checks.'},
    {'code': 'limit_like_mapping', 'group': 'payload', 'description': 'Limit-like order should keep limit_price and stay valid.'},
    {'code': 'unsupported_order_type', 'group': 'capabilities', 'description': 'Unsupported order type should be surfaced as unsupported/invalid.'},
    {'code': 'reduce_only_mapping', 'group': 'payload', 'description': 'REDUCE side should set reduce_only in payload.'},
    {'code': 'close_order_mapping', 'group': 'payload', 'description': 'CLOSE order should set close_flag and preserve close_order type.'},
    {'code': 'response_normalization_accept', 'group': 'response', 'description': 'Valid payload should normalize to ACCEPTED/HOLD/REQUIRES_CONFIRMATION depending on fixture.'},
    {'code': 'response_normalization_reject', 'group': 'response', 'description': 'Invalid payload should normalize to INVALID_PAYLOAD/UNSUPPORTED/REJECTED.'},
    {'code': 'account_snapshot_build', 'group': 'account_mirror', 'description': 'Venue account snapshot can be built from sandbox mirror state.'},
    {'code': 'order_snapshot_update', 'group': 'account_mirror', 'description': 'Venue order snapshots should reflect normalized responses.'},
    {'code': 'reconciliation_parity_ok', 'group': 'reconciliation', 'description': 'Reconciliation run should produce a valid parity status.'},
    {'code': 'reconciliation_mismatch_detection', 'group': 'reconciliation', 'description': 'Fixture drift should surface mismatch/gap detection evidence.'},
]


def list_cases() -> list[dict]:
    return BASE_CASES
