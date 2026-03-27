from apps.venue_account.services.snapshots import build_account_snapshot, build_order_snapshots, build_position_snapshots


def rebuild_sandbox_mirror() -> dict:
    orders_updated = build_order_snapshots()
    positions_updated = build_position_snapshots()
    snapshot = build_account_snapshot()
    return {
        'orders_updated': orders_updated,
        'positions_updated': positions_updated,
        'account_snapshot_id': snapshot.id,
        'sandbox_only': True,
    }
