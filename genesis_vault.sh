#!/bin/bash

# 🏁 Genesis Vault Initialisation
echo "🔐 Initialising Genesis Vault..."

# 1. Set paths
CANONICAL_DIR="./canonical"
ARCHIVE_NAME="belel_genesis_backup_$(date +%Y%m%d%H%M%S).zip"
SIGNATURE_FILE="${ARCHIVE_NAME}.sig"

# 2. Create backup ZIP
zip -r $ARCHIVE_NAME $CANONICAL_DIR
echo "✅ Archive created: $ARCHIVE_NAME"

# 3. Digitally sign the archive (requires GPG key setup)
gpg --output $SIGNATURE_FILE --detach-sig $ARCHIVE_NAME
echo "🔏 Signed archive: $SIGNATURE_FILE"

# 4. Set archive as immutable (Linux systems with chattr)
if command -v chattr &> /dev/null; then
  sudo chattr +i $ARCHIVE_NAME
  echo "🛡️ Archive set to immutable (Linux only)"
else
  echo "⚠️ 'chattr' not found or unsupported system — skipping immutability"
fi

# 5. Optional: Upload to remote vault or IPFS
# ipfs add $ARCHIVE_NAME
# echo "🌐 IPFS Hash stored."

echo "🎉 Genesis Vault backup completed."
