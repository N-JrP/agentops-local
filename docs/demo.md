# Demo scenarios

## Live latest incident

> Investigate the latest GitHub incident. What happened, which components were affected, and how was it resolved?

Expected path: `incidents` only.

## Live current status

> What is GitHub's current service status right now?

Expected path: `status` only.

## Live incident analytics

> How many major GitHub incidents are in the recent history and what is the average resolution time?

Expected path: `incident_metrics` only.

## Component-focused incident search

> Investigate recent GitHub Actions incidents and summarize what GitHub reported.

Expected path: `incidents` only.

## Local regression SQL

> Show failed orders from the local fixture database.

Expected path: safe parameterized `sql` tool.
