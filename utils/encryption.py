import os
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class DiaryEncryption:
    def __init__(self, key_hex: str):
        key_bytes = bytes.fromhex(key_hex)
        if len(key_bytes) != 32:
            key_bytes = key_bytes.ljust(32, b"\x00")[:32]
        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        data = plaintext.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        result = nonce + ciphertext
        return base64.b64encode(result).decode("ascii")

    def decrypt(self, encrypted_str: str) -> str:
        raw = base64.b64decode(encrypted_str)
        nonce = raw[:12]
        ciphertext = raw[12:]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
