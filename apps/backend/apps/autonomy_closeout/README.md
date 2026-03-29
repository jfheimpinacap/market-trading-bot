# autonomy_closeout

`autonomy_closeout` cierra el loop posterior a `autonomy_disposition`:

- consolida campañas con disposition final
- genera `CampaignCloseoutReport` auditable
- deriva `CloseoutFinding` y `CloseoutRecommendation`
- emite handoff explícito (stub) para memoria, postmortem y feedback roadmap/scenario
- mantiene controles manual-first (`complete/<campaign_id>`)

Fuera de alcance: ejecución real broker/exchange, auto-learning opaco, auto-archivo sin control y auto-cambios de roadmap.
