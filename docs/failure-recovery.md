# Failure and recovery demonstration

Transient online-tool failures are retried according to `TOOL_MAX_ATTEMPTS` and `TOOL_RETRY_BACKOFF_SECONDS`.

If a required tool still fails after its normal retries, the graph performs one deterministic recovery/replan pass over failed required tools before synthesis. The execution trace records:

- attempt count
- retry errors
- recovery flag
- final status
- duration

If the final tool state is still failed, `requires_human_review=True`. If recovery succeeds, synthesis continues from the recovered evidence.

Unit tests in `tests/test_reliability.py` demonstrate both transient retry success and recovery-pass success without depending on the network.
