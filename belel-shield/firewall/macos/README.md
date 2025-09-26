# macOS Packet Filter (pf)

Apply rules:
```bash
sudo cp belel-shield/firewall/macos/pf.conf /etc/pf.conf
sudo pfctl -f /etc/pf.conf
sudo pfctl -e
```

Schedule daily re-apply (optional):
```bash
cp belel-shield/firewall/macos/com.belel.firewall.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.belel.firewall.plist
```
Revert:
```bash
sudo pfctl -d
```
