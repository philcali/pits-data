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
                        'login',
                        'invoke',
                        'listSessions',
                    ]
                },
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$default")

    mock_client.assert_called_once()


def test_connect_invalid(connections):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': '$connect',
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Invalid subprotocol. Expected manager or child'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$connect")

    mock_client.assert_called_once()


def test_connect(connections):
    connectDb = app_context.resolve()['connections']

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': '$connect',
                'statusCode': 200,
                'body': {
                    'connectionId': ConnectionId,
                },
            }
        })

    exp = floor(time.time()) + 60 * 1000
    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(
            routeKey="$connect",
            headers={
                'Sec-Websocket-Protocol': 'manager',
            },
            authorizer={
                "sub": "98498077-4c1d-4ffb-ab3d-8532dce5db4d",
                "event_id": "f2c58f6d-3bc5-45ed-8a04-885d7f685f66",
                "token_use": "id",
                "exp": exp,
            })

    mock_client.assert_called_once()
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
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$connect", connectionId="abc-123", headers={
            'ManagerId': "$connectionId",
            'Sec-Websocket-Protocol': 'child',
        })

    mock_client.assert_called_once()


def test_disconnect_session(connections):

    management = MagicMock()
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$disconnect", connectionId="abc-123")

    mock_client.assert_called_once()
