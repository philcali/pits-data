import logging
import os
import time
from jose import jwt, jwk
from jose.utils import base64url_decode
from ophis import set_stream_logger
from requests import get


logger = logging.getLogger('jwt')


class JWTAuthorizer:
    def __init__(self, audience, keys) -> None:
        self.audience = audience
        self.keys = keys

    def pull_known_keys(pool_id, region=None):
        aws_region = os.getenv("AWS_REGION") if region is None else region
        res = get('/'.join([
            f'https://cognito-idp.{aws_region}.amazonaws.com',
            pool_id,
            '.well-known',
            'jwks.json',
        ]))
        res.raise_for_status()
        payload = res.json()
        return payload['keys']

    def generate_policy(principal, effect, resource, context={}):
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
            },
            'context': {
                **context,
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
            return None
        public_key = jwk.construct(self.keys[key_index])
        message, encoded_signature = str(token).rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        if not public_key.verify(message.encode('utf-8'), decoded_signature):
            logger.info(f'Cloud not verify public key: {self.keys[key_index]}')
            return None
        claims = jwt.get_unverified_claims(token)
        logger.debug(f'Verified claims {claims}')
        if time.time() > claims['exp']:
            logger.info("Provided token was expired.")
            return None
        if claims['aud'] != self.audience:
            logger.info(f"Provided token did not matach {self.audience}")
            return None
        return claims


def user_jwt(event, context):
    set_stream_logger('jwt')
    connectionId = event['requestContext']['connectionId']
    token = event['headers'].get('Authorization', None)
    if token is None:
        logger.info('Event did not contain an Authorization header.')
        return JWTAuthorizer.generate_policy(connectionId, 'Deny', event['methodArn'])
    logger.debug(f'Provided token {token}')
    try:
        keys = JWTAuthorizer.pull_known_keys(os.getenv("USER_POOL_ID"))
        authorizer = JWTAuthorizer(os.getenv("USER_CLIENT_ID"), keys)
        claims = authorizer.authorize(token=token)
        if claims is not None:
            return JWTAuthorizer.generate_policy(
                principal=connectionId,
                effect='Allow',
                resource=event['methodArn'],
                context=claims)
    except Exception as e:
        logger.error('Failed to create authorizer:', exc_info=e)
    return JWTAuthorizer.generate_policy(connectionId, 'Deny', event['methodArn'])
