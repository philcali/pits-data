import json
import logging
import os
from ophis.database import Repository
from ophis.globals import app_context, request
from pinthesky.auth import JWTAuthorizer
from pinthesky.database import DataTokens
from pinthesky.resource import api, management


app_context.inject('data_tokens', DataTokens())
logger = logging.getLogger(__name__)


@api.routeKey('login')
def login(connections, data_tokens):
    """
    The "login" action will authorize the connection based an exchange token
    created in the control plane. The token is single use, and tied to a
    valid identity established from a user pool. A connection will send the
    following payload:

    {
        "action": "login",
        "payload": {
            "tokenId": "<control plane token>",
            "jwtId": "<session token from user pool>"
        }
    }

    It is possible for a "session" connection to link to a "manager"
    connection by providing the "managerId" in the payload.
    """

    input = json.loads(request.body).get('payload', {})
    connection_id = input.get('managerId', request.request_context('connectionId'))
    connection = connections.get(
        request.account_id(),
        item_id=request.request_context('connectionId'),
    )
    payload = {'statusCode': 200}

    if input.get('managerId', None) is not None:
        manager = connections.get(
            request.account_id(),
            item_id=input['managerId'],
        )
        if manager is None:
            logger.warning(f'The specified manager {input["managerId"]} does not exist')
            del input['managerId']
            connection_id = request.request_context('connectionId')

    @management.post(connectionId=connection_id)
    def post_to_connection():
        return payload

    def post_access_denied(reason):
        payload['statusCode'] = 401
        payload['error'] = {
            'code': 'AccessDenied',
            'message': reason,
        }
        return post_to_connection()

    if connection is None:
        return post_access_denied('Connection is not valid')

    if connection['authorized']:
        payload['body'] = {'authorized': True}
        return post_to_connection()

    for field in ['tokenId', 'jwtId']:
        if field not in input:
            payload['statusCode'] = 400
            payload['error'] = {
                'code': 'InvalidInput',
                'message': f'Input payload {field} is invalid'
            }
            return post_to_connection()

    claims = None
    try:
        jwt = JWTAuthorizer(
            os.getenv('USER_CLIENT_ID'),
            JWTAuthorizer.pull_known_keys(
                os.getenv('USER_POOL_ID'),
            )
        )
        claims = jwt.authorize(input['jwtId'])
    except Exception as e:
        logger.error('Failed to authorize jwt token: ', exc_info=e)

    if claims is None:
        return post_access_denied('JWT token is not valid')

    token = data_tokens.get(
        request.account_id(),
        item_id=input['tokenId'],
    )

    if token is None or token['authorization']['activated']:
        return post_access_denied('Token is not valid')

    updates = [
        {
            'repository': data_tokens,
            'item': {
                'id': input['tokenId'],
                'createTime': token['createTime'],
                'expiresIn': token['expiresIn'],
                'authorization': {
                    'connectionId': request.request_context('connectionId'),
                    'activated': True,
                }
            }
        },
        {
            'repository': connections,
            'item': {
                'connectionId': connection['connectionId'],
                'createTime': connection['createTime'],
                'managerId': input.get('managerId', None),
                'manager': input.get('managerId', None) is None,
                'authorized': True,
                'claims': claims,
                'expiresIn': claims['exp'],
            }
        }
    ]

    if input.get('managerId', None) is not None:
        updates.append({
            'repository': connections,
            'parent_ids': ['Manager', input['managerId']],
            'item': {
                'connectionId': request.request_context('connectionId'),
                'authorized': True,
                'claims': claims,
                'expiresIn': claims['exp'],
            }
        })

    Repository.batch_write(request.account_id(), updates=updates)
    payload['body'] = {
        'authorized': True,
        'connectionId': request.request_context('connectionId')
    }
    return post_to_connection()
