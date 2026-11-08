$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
& (Join-Path $PSScriptRoot 'with_keys.ps1') `
    -EnvFile 'C:/Users/david/Documents/GitHub/classifier-for-metagaming/.env' `
    -Program (Join-Path $taskRoot '.venv/Scripts/python.exe') `
    -ProgramArgs @('-I', (Join-Path $PSScriptRoot 'agent_run_supervisor.py'))
exit $LASTEXITCODE
