import boto3
import json
import os
from ophis.globals import app_context
from requests import exceptions
from unittest.mock import patch, MagicMock
from test_auth import ENDPOINT, FAKE_KEYS, FAKE_TOKEN
from uuid import uuid4


def test_login_not_found(auth):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == 'not-found-id'
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 401,
                'error': {
                    'code': 'AccessDenied',
                    'message': 'Connection is not valid',
                },
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId='not-found-id', body={})

    mock_client.assert_called_once()


def test_login_already_authorized(auth):
    connectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': True,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 200,
                'body': {
                    'authorized': True
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId=connectionId, body={})

    mock_client.assert_called_once()


def test_login_input_input(auth):
    connectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': False,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload tokenId is invalid'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId=connectionId, body={})

    mock_client.assert_called_once()


@patch('time.time', MagicMock(return_value=1711747711))
def test_login_jwt_failed(requests_mock, auth):
    requests_mock.get(ENDPOINT, exc=exceptions.ConnectTimeout)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'

    connectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': False,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 401,
                'error': {
                    'code': 'AccessDenied',
                    'message': 'JWT token is not valid'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId=connectionId, body={
            'payload': {
                'tokenId': 'abc-123',
                'jwtId': FAKE_TOKEN,
            }
        })

    mock_client.assert_called_once()


@patch('time.time', MagicMock(return_value=1711747711))
def test_login_token_not_found(requests_mock, auth):
    requests_mock.get(ENDPOINT, json=FAKE_KEYS)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    os.environ['USER_CLIENT_ID'] = '27pk3aoia2l347oq7si0v8j3mb'

    connectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': False,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 401,
                'error': {
                    'code': 'AccessDenied',
                    'message': 'Token is not valid'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId=connectionId, body={
            'payload': {
                'tokenId': 'abc-123',
                'jwtId': FAKE_TOKEN,
            }
        })

    mock_client.assert_called_once()


@patch('time.time', MagicMock(return_value=1711747711))
def test_login_token_successful_login(requests_mock, auth):
    requests_mock.get(ENDPOINT, json=FAKE_KEYS)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    os.environ['USER_CLIENT_ID'] = '27pk3aoia2l347oq7si0v8j3mb'

    connectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': False,
        }
    )

    tokenId = str(uuid4())
    tokens = app_context.resolve()['data_tokens']
    tokens.create(
        '123456789012',
        item={
            'id': tokenId,
            'authorization': {
                'activated': False,
            }
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 200,
                'body': {
                    'authorized': True,
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId=connectionId, body={
            'payload': {
                'tokenId': tokenId,
                'jwtId': FAKE_TOKEN,
            }
        })

    mock_client.assert_called_once()
    updated_token = tokens.get('123456789012', item_id=tokenId)
    assert updated_token['authorization'] == {
        'connectionId': connectionId,
        'activated': True
    }


@patch('time.time', MagicMock(return_value=1711747711))
def test_login_token_through_manager(requests_mock, auth):
    requests_mock.get(ENDPOINT, json=FAKE_KEYS)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    os.environ['USER_CLIENT_ID'] = '27pk3aoia2l347oq7si0v8j3mb'

    connectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': False,
        }
    )

    managerId = str(uuid4())
    connections.create(
        '123456789012',
        item={
            'connectionId': managerId,
            'authorized': True,
        }
    )

    tokenId = str(uuid4())
    tokens = app_context.resolve()['data_tokens']
    tokens.create(
        '123456789012',
        item={
            'id': tokenId,
            'authorization': {
                'activated': False,
            }
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == managerId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'login',
                'statusCode': 200,
                'body': {
                    'authorized': True,
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        auth(routeKey="login", connectionId=connectionId, body={
            'payload': {
                'managerId': managerId,
                'tokenId': tokenId,
                'jwtId': FAKE_TOKEN,
            }
        })

    mock_client.assert_called_once()
    updated_token = tokens.get('123456789012', item_id=tokenId)
    assert updated_token['authorization'] == {
        'connectionId': connectionId,
        'activated': True
    }
    updated_connection = connections.get('123456789012', item_id=connectionId)
    assert updated_connection['managerId'] == managerId
    assert not updated_connection['manager']
