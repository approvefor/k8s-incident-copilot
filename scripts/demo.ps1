$ErrorActionPreference = "Stop"

$baseUrl = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8000" }

function Write-Step($message) {
  Write-Host ""
  Write-Host "==> $message" -ForegroundColor Cyan
}

Write-Step "Starting local stack"
docker compose up --build -d

Write-Step "Waiting for API readiness"
$ready = $false
for ($i = 1; $i -le 30; $i++) {
  try {
    Invoke-RestMethod -Uri "$baseUrl/readyz" -Method Get | Out-Null
    $ready = $true
    break
  } catch {
    Start-Sleep -Seconds 2
  }
}
if (-not $ready) {
  throw "API did not become ready"
}

Write-Step "Injecting incident logs"
$logs = @(
  @{ service = "api"; level = "ERROR"; message = "database timeout while processing checkout request"; trace_id = "demo-timeout-1" },
  @{ service = "api"; level = "ERROR"; message = "connection pool exhausted after recent deploy"; trace_id = "demo-timeout-2" },
  @{ service = "gateway"; level = "WARNING"; message = "upstream latency above SLO threshold"; trace_id = "demo-timeout-3" }
)

foreach ($log in $logs) {
  Invoke-RestMethod -Uri "$baseUrl/logs" -Method Post -Body ($log | ConvertTo-Json) -ContentType "application/json" | Out-Null
}

$incidentBody = @{
  service = "api"
  query = "database timeout and high latency after deploy"
  mode = "suggest"
  actor = "demo-user"
} | ConvertTo-Json

Write-Step "AI SRE triage report"
$incident = Invoke-RestMethod -Uri "$baseUrl/incidents/analyze" -Method Post -Body $incidentBody -ContentType "application/json"
$incident | ConvertTo-Json -Depth 8

Write-Step "Policy-checked action plan"
Invoke-RestMethod -Uri "$baseUrl/actions/plan" -Method Post -Body $incidentBody -ContentType "application/json" |
  ConvertTo-Json -Depth 8

Write-Step "Denied dangerous action demo"
$denied = @{
  action = "get_secret"
  target = "api"
  namespace = "ai-platform"
  approved = $true
  dry_run = $true
  actor = "demo-user"
  reason = "AI should never access secrets"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/actions/execute" -Method Post -Body $denied -ContentType "application/json" |
  ConvertTo-Json -Depth 8

Write-Step "Audit trail"
Invoke-RestMethod -Uri "$baseUrl/audit/events?limit=10" -Method Get | ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "Demo complete: $baseUrl/docs" -ForegroundColor Green
