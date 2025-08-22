# Verify BLP Identity (Public)

## 1) File integrity
```bash
cd blp-identity
shasum -a 256 images/*.jpg images/*.png BLP_* LICENSE-BLP.txt > _local.txt
diff -u checksums.txt _local.txt
