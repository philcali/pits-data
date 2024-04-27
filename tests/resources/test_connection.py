import boto3
import json
import time
from math import floor
from ophis.globals import app_context
from pinthesky.util import iterate_all_items
from unittest.mock import MagicMock, patch


def test_iterate(connections):
    connectionsDB = app_context.resolve()['connections']
    unique_cons = []
    for index in range(1, 200):
        connection = connectionsDB.create(
            '111111111111',
            item={'connectionId': f'connectionId-{index}'}
        )
        unique_cons.append(connection)

    run = False
    for connection in iterate_all_items(connectionsDB, '111111111111'):
        run = True
        assert connection in unique_cons
    assert run


def test_default(connections):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': '$default',
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'Resource not found',
                },
                'body': {
                    'availableActions': [
                        'status',
                        'invoke',
                        'listSessions',
                        'login',
                    ]
                },
                'requestId': 'id',
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$default")

    mock_client.assert_called_once()


def test_connect_invalid(connections):
    resp = connections(routeKey="$connect")
    assert resp.code == 400


def test_connect(connections):
    connectDb = app_context.resolve()['connections']
    exp = floor(time.time()) + 60 * 1000
    resp = connections(
        routeKey="$connect",
        headers={
            'Sec-WebSocket-Protocol': 'manager',
        },
        authorizer={
            "sub": "98498077-4c1d-4ffb-ab3d-8532dce5db4d",
            "event_id": "f2c58f6d-3bc5-45ed-8a04-885d7f685f66",
            "token_use": "id",
            "exp": exp,
        })
    assert resp.code == 200

    connect = connectDb.get(
        '123456789012',
        item_id='$connectionId'
    )
    assert connect['authorized']
    assert connect['expiresIn'] == exp


def test_connect_session(connections):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': '$connect',
                'statusCode': 200,
                'body': {
                    'connectionId': "abc-123",
                },
                'requestId': 'id',
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$connect", connectionId="abc-123", headers={
            'ManagerId': "$connectionId",
            'Sec-WebSocket-Protocol': 'session',
        })

    mock_client.assert_called_once()


def test_disconnect_session(connections):

    management = MagicMock()
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$disconnect", connectionId="abc-123")

    mock_client.assert_called_once()


def test_status_not_found(connections):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-found"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'status',
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection not-found was not found'
                },
                'requestId': 'id',
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="status", connectionId="not-found", body={
        })

    mock_client.assert_called_once()


def test_status_not_authorized(connections):

    connectionDb = app_context.resolve()['connections']
    connectionDb.create(
        connections.account_id(),
        item={
            'connectionId': 'not-authorized'
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-authorized"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'status',
                'statusCode': 401,
                'error': {
                    'code': 'Unauthorized',
                    'message': 'The connection not-authorized is not authorized'
                },
                'requestId': 'id',
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="status", connectionId="not-authorized", body={
        })

    mock_client.assert_called_once()


def test_status_happy_path(connections):

    connectionDb = app_context.resolve()['connections']
    connection = connectionDb.create(
        connections.account_id(),
        item={
            'connectionId': 'happy-path',
            'authorized': True,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "happy-path"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'status',
                'statusCode': 200,
                'body': connection,
                'requestId': 'id',
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="status", connectionId="happy-path", body={
        })

    mock_client.assert_called_once()
