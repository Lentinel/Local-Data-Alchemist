$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPort = 8002
$frontendPort = 5173

$ports = @($backendPort, $frontendPort)
foreach ($port in $ports) {
  $connections = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  if (-not $connections) {
    continue
  }
  $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $pids) {
    if ($procId) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
  }
}

$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

$backendProc = Start-Process -FilePath "python" -ArgumentList @(
  "-m", "uvicorn", "main:app",
  "--reload",
  "--host", "0.0.0.0",
  "--port", "$backendPort"
) -WorkingDirectory $backendDir -PassThru

Start-Sleep -Milliseconds 900

Set-Location $frontendDir
$env:VITE_API_TARGET = "http://localhost:$backendPort"
npm run dev
