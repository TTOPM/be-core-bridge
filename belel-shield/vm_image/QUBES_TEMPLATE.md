# Qubes Template for Belel Shield

- Create a Debian TemplateVM: `debian-12-belel`
- Install: `sudo apt-get update && sudo apt-get install -y nftables jq python3-pip`
- Copy repo to TemplateVM `/usr/local/belel-shield`
- AppVM policy:
  - NetVM: your TorVM or VPNVM
  - qvm-service enable `belel-firewall`
- Hook firewall: systemd user unit runs `belel_firewall.sh` on start
- Private storage per AppVM: `~/.belel`
