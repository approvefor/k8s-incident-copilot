$ErrorActionPreference = "Stop"

$namespace = if ($env:NAMESPACE) { $env:NAMESPACE } else { "ai-platform" }

Write-Host "Current API pods:"
kubectl get pods -n $namespace -l app.kubernetes.io/component=api

$pod = kubectl get pods -n $namespace -l app.kubernetes.io/component=api -o jsonpath="{.items[0].metadata.name}"
if (-not $pod) {
  throw "No API pod found in namespace '$namespace'."
}

Write-Host "Deleting pod $pod to demonstrate self-healing..."
kubectl delete pod -n $namespace $pod

Write-Host "Waiting for rollout to become healthy..."
kubectl rollout status deployment/ai-platform-ai-platform-api -n $namespace --timeout=120s

Write-Host "API pods after recovery:"
kubectl get pods -n $namespace -l app.kubernetes.io/component=api
