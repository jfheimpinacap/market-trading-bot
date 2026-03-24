# provider-core

Shared read-only abstractions for external market data providers.

## Current scope (read-only)
- Common `ReadOnlyProviderClient` interface for listing/getting markets.
- Shared normalized schema via `NormalizedMarketRecord`.
- Lightweight HTTP JSON helper with consistent error wrapping.

## Out of scope
- Trading authentication.
- Order placement/cancelation.
- Real execution adapters.
