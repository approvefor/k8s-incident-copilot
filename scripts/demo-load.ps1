$ErrorActionPreference = "Stop"

for ($i = 1; $i -le 20; $i++) {
  $level = @("INFO", "WARNING", "ERROR", "CRITICAL") | Get-Random
  $service = @("checkout", "payments", "inventory", "gateway") | Get-Random
  $body = @{
    service = $service
    level = $level
    message = "synthetic $level event from $service during deploy window"
    trace_id = "demo-$i"
  } | ConvertTo-Json

  Invoke-RestMethod -Uri "http://localhost:8000/logs" -Method Post -Body $body -ContentType "application/json"
}
