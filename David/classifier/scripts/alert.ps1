param([Parameter(Mandatory=$true)][string]$Message)
$escapedMessage = $Message.Replace("'", "''")
$alertCommand = "(New-Object Media.SoundPlayer 'C:\Windows\Media\Alarm01.wav').PlayLooping(); Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('$escapedMessage','Runtime build needs you','OK','Warning') | Out-Null"
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-Command',$alertCommand
