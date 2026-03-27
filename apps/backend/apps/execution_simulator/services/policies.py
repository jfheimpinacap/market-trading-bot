from dataclasses import dataclass
from decimal import Decimal

from apps.execution_simulator.models import ExecutionPolicyProfile


@dataclass(frozen=True)
class PolicyConfig:
    slug: str
    slippage_bps: int
    partial_fill_ratio: Decimal
    max_wait_cycles: int
    cancel_after_n_cycles: int
    min_liquidity_for_auto_fill: Decimal


POLICIES: dict[str, PolicyConfig] = {
    ExecutionPolicyProfile.OPTIMISTIC: PolicyConfig(
        slug=ExecutionPolicyProfile.OPTIMISTIC,
        slippage_bps=20,
        partial_fill_ratio=Decimal('0.75'),
        max_wait_cycles=5,
        cancel_after_n_cycles=0,
        min_liquidity_for_auto_fill=Decimal('2000'),
    ),
    ExecutionPolicyProfile.BALANCED: PolicyConfig(
        slug=ExecutionPolicyProfile.BALANCED,
        slippage_bps=45,
        partial_fill_ratio=Decimal('0.50'),
        max_wait_cycles=3,
        cancel_after_n_cycles=0,
        min_liquidity_for_auto_fill=Decimal('5000'),
    ),
    ExecutionPolicyProfile.CONSERVATIVE: PolicyConfig(
        slug=ExecutionPolicyProfile.CONSERVATIVE,
        slippage_bps=70,
        partial_fill_ratio=Decimal('0.35'),
        max_wait_cycles=2,
        cancel_after_n_cycles=1,
        min_liquidity_for_auto_fill=Decimal('10000'),
    ),
}


def get_policy(profile_slug: str | None) -> PolicyConfig:
    if not profile_slug:
        return POLICIES[ExecutionPolicyProfile.BALANCED]
    return POLICIES.get(profile_slug, POLICIES[ExecutionPolicyProfile.BALANCED])
