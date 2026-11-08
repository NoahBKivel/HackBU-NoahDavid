param([Parameter(Mandatory=$true)][string]$EnvFile,
      [Parameter(Mandatory=$true)][string]$Program,
      [Parameter(ValueFromRemainingArguments=$true)][string[]]$ProgramArgs)
$ErrorActionPreference = 'Stop'
foreach ($line in [IO.File]::ReadLines($EnvFile)) {
    if ($line -match '^\s*(?:export\s+)?(ANTHROPIC_API_KEY|HF_TOKEN)\s*=\s*(.*?)\s*$') {
        $name = $Matches[1]
        $value = $Matches[2].Trim().Trim('"').Trim("'")
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}
try {
    & $Program @ProgramArgs
    $resultCode = $LASTEXITCODE
} finally {
    Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:HF_TOKEN -ErrorAction SilentlyContinue
}
exit $resultCode
