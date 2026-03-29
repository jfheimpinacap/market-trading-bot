# autonomy_scheduler

`autonomy_scheduler` is the campaign admission board and safe-start window planner for pending autonomy campaigns.

## Scope
- Maintains an auditable campaign admission queue (`CampaignAdmission`).
- Tracks safe start windows (`ChangeWindow`).
- Produces auditable scheduler planning runs (`SchedulerRun`) with recommendations (`AdmissionRecommendation`).
- Keeps operations manual-first: recommendations + explicit admit/defer actions only.

## Boundaries
- Does **not** replace `autonomy_program` (active campaign coexistence).
- Does **not** replace `autonomy_campaign` (wave/step/checkpoint execution).
- Does **not** introduce auto-start, real-money execution, or opaque planners.
