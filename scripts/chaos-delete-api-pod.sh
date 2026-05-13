#!/usr/bin/env sh
set -eu

NAMESPACE="${NAMESPACE:-ai-platform}"

echo "Current API pods:"
kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=api

POD="$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}')"
if [ -z "$POD" ]; then
  echo "No API pod found in namespace '$NAMESPACE'." >&2
  exit 1
fi

echo "Deleting pod $POD to demonstrate self-healing..."
kubectl delete pod -n "$NAMESPACE" "$POD"

echo "Waiting for rollout to become healthy..."
kubectl rollout status deployment/ai-platform-ai-platform-api -n "$NAMESPACE" --timeout=120s

echo "API pods after recovery:"
kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=api
