# Limitations

- GitHub Status provides public customer-facing incident information, not GitHub's private raw logs or internal telemetry.
- Incident analytics are derived from the public recent-incident feed and should not be described as GitHub internal production metrics.
- Local Ollama latency depends strongly on the user's CPU/GPU and model size.
- The public source can be temporarily unavailable; offline tests therefore use deterministic fixtures.
- Kubernetes uses host Ollama for a laptop-friendly demo rather than running the multi-GB model inside the cluster.
- Redis and pgvector are intentionally omitted because the current workload has no caching or vector-retrieval requirement.
