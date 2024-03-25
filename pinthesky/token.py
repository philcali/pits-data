from base64 import b64decode, b64encode
from decimal import Decimal
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import json


class TokenMarshaller:
    def encrypt(self, hash_key, header, last_key):
        pass

    def decrypt(self, hash_key, header, next_token):
        pass


class EncryptedTokenMarshaller(TokenMarshaller):
    def __init__(self, mode=AES.MODE_GCM) -> None:
        self.__mode = mode

    def __generate_key(self, account_id):
        return SHA256.new(bytes(account_id, 'utf-8')).digest()

    def __to_dto_key(self, last_key):
        new_val = {}
        for key, value in last_key.items():
            val = value
            if isinstance(val, Decimal):
                val = {'__internal': 'Decimal', 'value': int(value)}
            new_val[key] = val
        return new_val

    def __from_dto_key(self, last_key):
        new_val = {}
        for key, value in last_key.items():
            val = value
            if isinstance(val, dict) and '__internal' in val:
                val = globals()[val['__internal']](val['value'])
            new_val[key] = val
        return new_val

    def encrypt(self, hash_key, header, last_key):
        if last_key is None:
            return None
        cipher = AES.new(
            key=self.__generate_key(hash_key),
            mode=self.__mode)
        cipher.update(bytes(header, 'utf-8'))
        data = bytes(json.dumps(self.__to_dto_key(last_key)), 'utf-8')
        ciphertext, tag = cipher.encrypt_and_digest(data)
        token_payload = {
            'nonce': b64encode(cipher.nonce).decode('utf-8'),
            'payload': b64encode(ciphertext).decode('utf-8'),
            'tag': b64encode(tag).decode('utf-8')
        }
        token_bytes = bytes(json.dumps(token_payload), 'utf-8')
        return b64encode(token_bytes).decode('utf-8')

    def decrypt(self, hash_key, header, next_token):
        if next_token is None:
            return None
        values = json.loads(b64decode(next_token).decode('utf-8'))
        cipher = AES.new(
            key=self.__generate_key(hash_key),
            mode=self.__mode,
            nonce=b64decode(values['nonce']))
        cipher.update(bytes(header, 'utf-8'))
        plaintext = cipher.decrypt_and_verify(
            b64decode(values['payload']),
            b64decode(values['tag']))
        return self.__from_dto_key(json.loads(plaintext))
