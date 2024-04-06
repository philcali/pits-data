import boto3
import json
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
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'Resource not found',
                },
                'body': {
                    'availableActions': [
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


def test_connect(connections):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 200,
                'body': {
                    'connectionId': ConnectionId,
                },
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$connect")

    mock_client.assert_called_once()


def test_connect_session(connections):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
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
            'ManagerId': "$connectionId"
        })

    mock_client.assert_called_once()


def test_disconnect_session(connections):

    management = MagicMock()
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        connections(routeKey="$disconnect", connectionId="abc-123", headers={
            'ManagerId': "$connectionId"
        })

    mock_client.assert_called_once()
