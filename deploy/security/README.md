# Security Model

This MVP includes Kubernetes security primitives and documents the production path.

- RBAC: run workloads with a dedicated ServiceAccount and minimal token mounting.
- Secrets: use Vault or External Secrets Operator instead of plain Kubernetes Secret manifests. See `externalsecret-example.yaml`.
- Network: use NetworkPolicy to restrict API ingress and egress.
- Runtime hardening: run containers as a non-root user, drop Linux capabilities, disable privilege escalation, and use the runtime default seccomp profile.
- TLS: terminate HTTPS through NGINX Ingress and cert-manager.
- WAF: put Cloudflare, AWS WAF, or another edge WAF in front of public endpoints.
- Supply chain: CI runs Trivy scans, publishes SBOM artifacts for pushed images,
  and signs container images with keyless Cosign.
- Admission control: `kyverno-policies.yaml` documents runtime hardening and
  digest-pinned immutable image checks for the API and worker pods.

OpenAI embeddings in Kubernetes require `OPENAI_API_KEY` in `ai-platform-secrets` and `networkPolicy.allowExternalHttps=true`.

Audit persistence uses `DATABASE_URL`. The Helm chart can generate it from the bundled PostgreSQL dependency, or you can provide a `database-url` key through External Secrets.

Production hardening checklist:

- pin image tags by digest
- enable admission policies
- sign images with Cosign
- enforce Cosign signature verification with Kyverno or another admission controller
- publish and retain SBOMs for each release image
- store audit logs centrally
- rotate credentials
