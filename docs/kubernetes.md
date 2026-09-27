# Local Kubernetes demo

AgentOps includes project-relevant Kubernetes primitives rather than Kubernetes for its own sake:

- Namespace: isolation for the demo stack
- ConfigMap: non-secret AgentOps runtime configuration
- Secret: PostgreSQL credential
- Deployments: backend, UI, PostgreSQL
- Services: backend, UI, PostgreSQL
- Readiness/liveness probes: backend and UI health checks
- Resource requests/limits: backend guardrails

For kind, run:

```powershell
.\scripts\k8s_demo.ps1
```

The script creates a local cluster when needed, builds images, loads them into kind, applies manifests, waits for rollouts, and prints service state. Ollama remains on the host to avoid duplicating the model in the cluster.
