# Evaluation

The project separates deterministic offline regression from real-source integration.

## Offline

`pytest -q` tests routing policy, security, validator behavior, SQL filtering, public-source parsing with fixtures, tool behavior, recovery, observability summary, and API structure.

`python -m backend.evaluation.run_policy_evaluation` checks the expected tool plan for every deterministic evaluation case without requiring Ollama or internet access. It is executed in CI.

`python -m backend.evaluation.run_evaluation` runs the full local-LLM regression evaluation and stores both JSON output and a persistent evaluation record.

## Live integration

`python -m backend.evaluation.run_live_source_check` verifies GitHub Status connectivity, latest-incident ingestion, current service state, and incident metrics derived at runtime.

The user-verified live run on 2026-09-22 showed 21 tests passing, Ruff clean, GitHub Status reachable, and the latest-incident agent path selecting only the `incidents` tool with a validated grounded answer.
