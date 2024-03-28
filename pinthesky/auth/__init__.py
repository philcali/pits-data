import logging
import json
import os
import time
import urllib.request
from jose import jwt, jwk
from jose.utils import base64url_decode
from ophis import set_stream_logger


logger = logging.getLogger(__name__)


class JWTAuthorizer:
    def __init__(self, audience, keys) -> None:
        self.audience = audience
        self.keys = keys
    
    def pull_known_keys(pool_id, region=None):
        with urllib.request.urlopen(f'https://cognito-idp.{os.getenv('AWS_REGION', region)}.amazonaws.com/{pool_id}/.well-known/jwks.json') as r:
            response = r.read()
        payload = json.loads(response.decode('utf-8'))
        return payload['keys']

    def generate_policy(principal, effect, resource):
        return {
            'principalId': principal,
            'policyDocument': {
                'Statement': [
                    {
                        'Effect': effect,
                        'Action': 'execute-api:Invoke',
                        'Resource': resource,
                    }
                ]
            }
        }
    
    def authorize(self, token):
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        key_index = -1
        for i in range(len(self.keys)):
            if kid == self.keys[i]['kid']:
                key_index = i
                break
        if key_index == -1:
            logger.info('Could not find an applicable public key.')
            return False
        public_key = jwk.construct(self.keys[key_index])
        message, encoded_signature = str(token).rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        if not public_key.verify(message.encode('utf-8'), decoded_signature):
            logger.info(f'Cloud not verify public key: {self.keys[key_index]}')
            return False
        claims = jwt.get_unverified_claims(token)
        logger.debug(f'Verified claims {claims}')
        if time.time() > claims['exp']:
            logger.info("Provided token was expired.")
            return False
        if claims['aud'] != self.audience:
            logger.info(f"Provided token did not matach {self.audience}")
            return False
        return True


def user_jwt(event, context):
    set_stream_logger(__name__)
    connectionId = event['requestContext']['connectionId']
    token = event['headers'].get('Authorization', None)
    if token is None:
        logger.info('Event did not contain an Authorization header.')
        return JWTAuthorizer.generate_policy(connectionId, 'Deny', event['methodArn'])
    logger.debug(f'Provided token {token}')
    keys = JWTAuthorizer.pull_known_keys(os.getenv("USER_POOL_ID"))
    authorizer = JWTAuthorizer(os.getenv("USER_CLIENT_ID"), keys)
    if authorizer.authorize(token):
        return JWTAuthorizer.generate_policy(connectionId, 'Allow', event['methodArn'])
    return JWTAuthorizer.generate_policy(connectionId, 'Deny', event['methodArn'])
