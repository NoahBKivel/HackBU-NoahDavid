$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$outputRoot = Join-Path $taskRoot 'results/agent-runs'
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$processArgs = @('-NoProfile', '-File', (Join-Path $PSScriptRoot 'agent_run_supervisor.ps1'))
$process = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $taskRoot `
    -ArgumentList $processArgs -RedirectStandardOutput (Join-Path $outputRoot 'supervisor.stdout.log') `
    -RedirectStandardError (Join-Path $outputRoot 'supervisor.stderr.log')
@{ launcher_pid = $process.Id; started_at = (Get-Date -Format o) } |
    ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $outputRoot 'launcher.json')
Write-Output "Supervisor launcher PID: $($process.Id)"
