# Safety and permissions

- Current tools are registered as read-only.
- Unknown tools are rejected before execution.
- Tool input length and null-byte checks are enforced centrally.
- A narrow prompt/tool-abuse guard blocks direct attempts to bypass system/tool policy.
- The graph contains a human-approval branch for future tools marked `write`.
- No write-capable external tool is enabled in the portfolio build, so no destructive action is possible through the current tool registry.
