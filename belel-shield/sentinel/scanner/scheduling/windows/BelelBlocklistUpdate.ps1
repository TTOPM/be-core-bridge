# Belel Shield – Windows Task Scheduler quick-setup
# EDIT THESE PATHS:
$PythonPath = "C:\Python311\python.exe"
$RepoUpdateScript = "$env:USERPROFILE\belel-shield\sentinel\scanner\update_blocklist.py"

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $RepoUpdateScript
$Trigger = New-ScheduledTaskTrigger -Daily -At 08:10
$Settings = New-ScheduledTaskSettingsSet -Compatibility Win8 -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

Register-ScheduledTask -TaskName "BelelBlocklistUpdate" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Daily Belel Shield blocklist refresh"
Write-Host "[+] Scheduled task 'BelelBlocklistUpdate' created for daily 08:10"
