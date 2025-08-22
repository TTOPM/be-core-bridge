#!/bin/bash

echo "🔧 Installing Git LFS (if not already installed)..."
brew install git-lfs || echo "Git LFS already installed."

echo "🔧 Initializing Git LFS..."
git lfs install

echo "📌 Tracking file types with Git LFS..."
git lfs track "*.zip"
git lfs track "*.wav"
git lfs track "*.pem"

echo "📄 Writing to .gitattributes..."
cat <<EOL > .gitattributes
*.zip filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.pem filter=lfs diff=lfs merge=lfs -text
EOL

echo "📁 Staging .gitattributes for commit..."
git add .gitattributes
git commit -m "Add Git LFS tracking for .zip, .wav, .pem"

echo "❌ Removing cached versions of tracked files from regular Git..."
git rm --cached BELEL_Sentience_Bridge_Complete.zip
git rm --cached audio/belel_entry_response.wav
git rm --cached BELEL_OVERRIDE_PUBLIC_KEY.pem

echo "➕ Re-adding files (now tracked via Git LFS)..."
git add BELEL_Sentience_Bridge_Complete.zip
git add audio/belel_entry_response.wav
git add BELEL_OVERRIDE_PUBLIC_KEY.pem

git commit -m "Move large files to Git LFS"

echo "🚀 Pushing to origin/main..."
git push origin main

echo "✅ All done! Visit your repo and confirm .gitattributes and LFS status."
