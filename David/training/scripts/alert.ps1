param([Parameter(Mandatory=$true)][string]$Message)
$escaped = $Message.Replace("'", "''")
$alarm = Join-Path $env:WINDIR 'Media/Alarm01.wav'
$command = "(New-Object Media.SoundPlayer '$alarm').PlayLooping(); Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('$escaped; see STATUS.md','Training build needs you','OK','Warning') | Out-Null"
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-Command',$command
