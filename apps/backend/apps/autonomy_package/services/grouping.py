def group_candidates(*, candidates: list[dict]) -> dict[tuple[str, str], list[dict]]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for candidate in candidates:
        key = (candidate['target_scope'], candidate['grouping_key'])
        grouped.setdefault(key, []).append(candidate)
    for rows in grouped.values():
        rows.sort(key=lambda row: (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].index(row['priority_level']), row['governance_decision']), reverse=True)
    return grouped
