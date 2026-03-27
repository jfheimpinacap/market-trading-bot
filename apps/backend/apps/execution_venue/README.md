# execution_venue

`execution_venue` defines the **canonical external execution contract** used to prepare future broker/exchange adapters while remaining fully sandbox-only.

## Scope
- Canonical venue payload (`VenueOrderPayload`) mapped from `BrokerOrderIntent`.
- Normalized venue response (`VenueOrderResponse`) with stable status codes.
- Adapter capability profile (`VenueCapabilityProfile`) to validate feature support without external connectivity.
- Paper-live parity harness (`VenueParityRun`) across broker dry-run, execution simulator context, and sandbox adapter response.

## Explicit non-goals
- No real credentials.
- No real broker/exchange connection.
- No live order placement.
- No account reconciliation.

## Default adapter
`NullSandboxVenueAdapter` is the default and only adapter in this stage. It always runs in simulated mode and sets `live_supported=false`.
