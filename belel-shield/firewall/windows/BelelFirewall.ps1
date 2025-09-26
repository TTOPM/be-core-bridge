# Run as Administrator
$Blocklist1 = "$env:USERPROFILE\.belel\belel-blocklist.json"
$Blocklist2 = "$env:USERPROFILE\.belel\merged-blocklist.json"
$BL = (Test-Path $Blocklist2) ? $Blocklist2 : $Blocklist1

if (!(Test-Path $BL)) { Write-Host "No blocklist found at $BL"; exit 0 }

$Json = Get-Content $BL | ConvertFrom-Json
$IPs = @()
foreach ($pair in $Json.ip_ranges) {
  $start = $pair[0]; $end = $pair[1]
  if ($start -eq $end) { $IPs += "$start" } else { $IPs += "$start/24" }
}
$IPs = $IPs | Sort-Object -Unique

$Group = "Belel Shield"
Get-NetFirewallRule -Group $Group | Remove-NetFirewallRule -ErrorAction SilentlyContinue

foreach ($cidr in $IPs) {
  New-NetFirewallRule -DisplayName "Belel Out $cidr" -Direction Outbound -Action Block -RemoteAddress $cidr -Group $Group | Out-Null
  New-NetFirewallRule -DisplayName "Belel In  $cidr" -Direction Inbound  -Action Block -RemoteAddress $cidr -Group $Group | Out-Null
}
Write-Host "[+] Applied" ($IPs.Count) "CIDRs to Windows Defender Firewall"
