$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPort = 8002
$frontendPort = 5173

function Stop-Port([int]$port) {
  $connections = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  if (-not $connections) {
    return $true
  }

  $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $pids) {
    if ($procId) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
  }

  Start-Sleep -Milliseconds 300
  $stillListening = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  return (-not $stillListening)
}

if (-not (Stop-Port $backendPort)) {
  $blocking = Get-NetTCPConnection -State Listen -LocalPort $backendPort -ErrorAction SilentlyContinue | Select-Object -First 1
  $blockingPid = $blocking.OwningProcess
  Write-Host "后端端口 $backendPort 被占用且无法终止（PID=$blockingPid）。" -ForegroundColor Red
  Write-Host "请用管理员权限关闭该进程，或修改 dev.ps1 / 后端端口配置后重试。" -ForegroundColor Yellow
  exit 1
}

if (-not (Stop-Port $frontendPort)) {
  $blocking = Get-NetTCPConnection -State Listen -LocalPort $frontendPort -ErrorAction SilentlyContinue | Select-Object -First 1
  $blockingPid = $blocking.OwningProcess
  Write-Host "前端端口 $frontendPort 被占用且无法终止（PID=$blockingPid）。" -ForegroundColor Red
  Write-Host "请用管理员权限关闭该进程，或修改 dev.ps1 / 前端端口配置后重试。" -ForegroundColor Yellow
  exit 1
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
