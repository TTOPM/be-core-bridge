# Release Signing (GPG)
gpg --full-generate-key
gpg --armor --export YOURKEYID > gpg/belel_public_key.asc
shasum -a 256 belel-shield/sentinel/blocklists/belel-blocklist.json > belel-shield/sentinel/blocklists/belel-blocklist.sha256
gpg --armor --detach-sign belel-shield/sentinel/blocklists/belel-blocklist.json
gpg --armor --detach-sign belel-shield/sentinel/blocklists/belel-blocklist.sha256
