from typing import Protocol

from apps.broker_bridge.models import BrokerOrderIntent
from apps.execution_venue.models import VenueCapabilityProfile, VenueOrderPayload, VenueOrderResponse
from apps.execution_venue.services.capabilities import get_or_create_default_capabilities
from apps.execution_venue.services.payloads import build_payload, validate_payload
from apps.execution_venue.services.responses import dry_run


class VenueAdapter(Protocol):
    def build_payload(self, intent: BrokerOrderIntent, metadata: dict | None = None) -> VenueOrderPayload: ...

    def validate_payload(self, payload: VenueOrderPayload) -> tuple[bool, list[str], list[str], list[str]]: ...

    def dry_run(self, payload: VenueOrderPayload, metadata: dict | None = None) -> VenueOrderResponse: ...

    def get_capabilities(self) -> VenueCapabilityProfile: ...


class NullSandboxVenueAdapter:
    name = 'null_sandbox'

    def get_capabilities(self) -> VenueCapabilityProfile:
        return get_or_create_default_capabilities()

    def build_payload(self, intent: BrokerOrderIntent, metadata: dict | None = None) -> VenueOrderPayload:
        return build_payload(intent=intent, capability=self.get_capabilities(), metadata=metadata)

    def validate_payload(self, payload: VenueOrderPayload) -> tuple[bool, list[str], list[str], list[str]]:
        return validate_payload(payload=payload, capability=self.get_capabilities())

    def dry_run(self, payload: VenueOrderPayload, metadata: dict | None = None) -> VenueOrderResponse:
        valid, reason_codes, warnings, _ = self.validate_payload(payload)
        return dry_run(payload=payload, valid=valid, reason_codes=reason_codes, warnings=warnings, metadata=metadata)
