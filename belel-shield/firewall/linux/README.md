# Linux Firewall (nftables)

- Requires: `nft`, `jq`
- Applies DROP rules for suspicious IP ranges from `~/.belel/merged-blocklist.json` or `belel-blocklist.json`.

## Enable
```bash
sudo cp belel-shield/firewall/linux/belel_firewall.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now belel_firewall.timer
# run now
bash belel-shield/firewall/linux/belel_firewall.sh
```

## Revert
```bash
sudo nft flush ruleset
```
