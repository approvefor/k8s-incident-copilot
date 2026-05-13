# Observability

Recommended stack:

- kube-prometheus-stack for Prometheus, Alertmanager, and Grafana
- Loki with Promtail or Grafana Alloy for logs
- Jaeger or Tempo for traces

Import `grafana-dashboard.json` to get a ready AI SRE Copilot dashboard for request rate, p95 latency, service errors, pod restarts, and recent Loki error logs.

Useful dashboard panels:

- API request rate: `sum(rate(api_requests_total[5m])) by (endpoint)`
- p95 latency: `histogram_quantile(0.95, sum(rate(api_request_latency_seconds_bucket[5m])) by (le, endpoint))`
- error logs: `sum(rate(logs_ingested_total{level=~"ERROR|CRITICAL"}[5m])) by (service)`
- pod CPU and memory from kube-state-metrics / cAdvisor

Alert ideas:

- high API p95 latency for 10 minutes
- error logs above baseline
- pod restart count increases
- Qdrant readiness failures

Tracing:

- Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger-collector.observability:4317`.
- The FastAPI service instruments HTTP requests and creates spans around Qdrant index/search calls.
