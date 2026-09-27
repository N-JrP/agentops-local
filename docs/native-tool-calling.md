# Planner loop vs native tool calling

The production-style portfolio path uses LangGraph because it makes planning state, retries, recovery, validation, and execution history explicit.

`backend/native_tool_calling.py` provides a comparison implementation using Ollama-native function calling. This demonstrates that AgentOps understands both patterns:

- **LangGraph planner:** explicit deterministic orchestration and state machine; chosen for the project.
- **Native function calling:** simpler model-directed tool loop; included as a comparison path.
