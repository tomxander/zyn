# Project knowledge

Copy this file to knowledge.md and edit it. Zyn adds its text to every model call (extraction,
AI review, clarification, Anvil proposals), so keep it short and factual. Each change shows in
the audit log, and answers given with an older version are never replayed for the new one.
Leave out anything confidential you would not send to the model you use.

## Terms
- Cluster: the instrument cluster ECU, not a compute cluster.
- Telltale: a warning or indicator lamp on the cluster display.
- KL15: ignition on (terminal 15).

## Units and values
- Speeds are in km/h, times in milliseconds unless the requirement says otherwise.
- "Within X ms" is a maximum, measured from the bus signal to the display change.

## Signals
- Signal names follow the DBC exactly, for example VehicleSpeed and FuelLevelPct.

## House rules for requirement wording
- "shall" is binding, "should" is a recommendation; do not treat them as the same.
- "As specified in the CAN matrix" is an accepted reference, not a missing value.
