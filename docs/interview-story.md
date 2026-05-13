# Interview Story

Use this project to tell a clear DevOps story:

1. I built a small AI product, but the main focus is the production platform around it.
2. The API exposes health, readiness, metrics, configurable embedding search, and incident explanation endpoints.
3. The worker creates operational logs so the platform has live data.
4. CI validates code, infrastructure, security, Helm manifests, images, and deployment.
5. Kubernetes runs the services with probes, resources, HPA, PDB, NetworkPolicy, non-root containers, and Ingress-ready TLS.
6. Observability is designed around Prometheus metrics, Loki logs, Grafana dashboards, and Jaeger traces.
7. A chaos script deletes an API pod and shows Kubernetes self-healing through Deployment rollout status.

Demo flow:

1. Start local dependencies with Docker Compose.
2. Generate logs through the worker or `scripts/demo-load.ps1`.
3. Search for an incident through `/search`.
4. Ask `/explain` for an AI-style summary and next steps.
5. Show `/metrics`, Helm templates, CI stages, the Grafana dashboard JSON, and the security notes.
6. Run the chaos script and show pod recovery.

Strong closing line:

> This is not a chatbot wrapper. It is a production-minded AI platform with deploy, observe, secure, and recover workflows.
