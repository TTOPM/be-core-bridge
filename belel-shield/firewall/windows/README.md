# Windows Defender Firewall

Run (as Administrator):
```powershell
.\BelelFirewall.ps1
```

Daily refresh:
```powershell
Register-ScheduledTask -TaskName "BelelFirewallDaily" -Xml (Get-Content .\BelelFirewall-Task.xml | Out-String)
```
Revert:
```powershell
Get-NetFirewallRule -Group "Belel Shield" | Remove-NetFirewallRule
```
