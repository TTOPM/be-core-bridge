# be_core_bridge/security/signer.py

"""
Belel Protocol – Cryptographic Signing Utility
Securely signs and verifies outbound Belel files using GPG or custom BelelSec.

Used for:
- Protocol governance files
- Manifest and Covenant docs
- Enforced authorship in global propagation
"""

import gnupg
import os
from datetime import datetime

class BelelSigner:
    def __init__(self, gpg_home=None):
        self.gpg = gnupg.GPG(gnupghome=gpg_home or os.path.expanduser("~/.gnupg"))
        self.key_fingerprint = None

    def import_private_key(self, key_data: str):
        """
        Imports a private key into the GPG keyring.
        """
        result = self.gpg.import_keys(key_data)
        self.key_fingerprint = result.fingerprints[0]
        return result

    def sign_file(self, file_path: str, output_path: str = None, detach=False, clearsign=True):
        """
        Signs a file using the imported GPG key.
        """
        if not self.key_fingerprint:
            raise Exception("No key fingerprint set. Import private key first.")

        with open(file_path, 'rb') as f:
            if clearsign:
                signed_data = self.gpg.sign_file(
                    f, keyid=self.key_fingerprint, clearsign=True, detach=detach, output=output_path
                )
            else:
                signed_data = self.gpg.sign_file(
                    f, keyid=self.key_fingerprint, detach=detach, output=output_path
                )

        if not signed_data:
            raise Exception("Signing failed.")

        if output_path:
            return output_path
        return str(signed_data)

    def verify_signature(self, signed_path: str):
        """
        Verifies a GPG-signed file.
        """
        with open(signed_path, 'rb') as f:
            verified = self.gpg.verify_file(f)
        return verified

    def sign_message(self, message: str):
        """
        Signs a raw message string.
        """
        if not self.key_fingerprint:
            raise Exception("No key fingerprint set.")
        return self.gpg.sign(message, keyid=self.key_fingerprint)

    def get_metadata(self, signed_file_path: str):
        """
        Extracts metadata from a signed file.
        """
        verification = self.verify_signature(signed_file_path)
        return {
            "fingerprint": verification.fingerprint,
            "status": verification.status,
            "trust": verification.trust_text,
            "signer": verification.username,
            "timestamp": datetime.utcfromtimestamp(verification.timestamp).isoformat() if verification.timestamp else None
        }
