# Prediction Agent (MVP)

Prediction agent local-first para paper/demo mode:

- Construye `PredictionFeatureSnapshot` por mercado.
- Calcula `system_probability`, `market_probability`, `edge`, `confidence` y `rationale`.
- Persiste `PredictionRun` + `PredictionScore` para trazabilidad/auditoría.
- Usa `PredictionModelProfile` para perfiles heurísticos desacoplados.

Esta versión **no** hace ejecución real ni dinero real, y **no** reemplaza policy/risk/safety.
Está diseñada para evolucionar a un scorer entrenado (por ejemplo XGBoost) sin romper contratos de API.
