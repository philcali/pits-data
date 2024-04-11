import boto3
import json
import time
from math import floor
from ophis.globals import app_context
from unittest.mock import MagicMock, patch
from uuid import uuid4


def test_invoke_unauthorized(iot):
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
                'action': 'invoke',
                'statusCode': 401,
                'error': {
                    'code': 'AccessDenied',
                    'message': f'Connection {connectionId} is not authorized',
                },
                'requestId': 'id'
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={})

    mock_client.assert_called_once()


def test_invoke_validate(iot):
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
                'action': 'invoke',
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload camera is invalid',
                },
                'requestId': 'id'
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={})

    mock_client.assert_called_once()


def test_invoke_validate_event(iot):
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
                'action': 'invoke',
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload name is invalid',
                },
                'requestId': 'id'
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={
            'payload': {
                'camera': 'PitsCamera1',
                'event': {
                }
            }
        })

    mock_client.assert_called_once()


def test_invoke_validate_session(iot):
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
                'action': 'invoke',
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload session is invalid',
                },
                'requestId': 'id'
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={
            'payload': {
                'camera': 'PitsCamera1',
                'event': {
                    'name': 'recording',
                    'session': {
                        'start': True,
                        'stop': True
                    }
                }
            }
        })

    mock_client.assert_called_once()


def test_invoke_non_session(iot):
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
                'action': 'invoke',
                'statusCode': 200,
                'body': {
                    'invokeId': 'abc-123'
                },
                'requestId': 'efg-456'
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={
            'payload': {
                'invokeId': 'abc-123',
                'camera': 'PitsCamera1',
                'event': {
                    'name': 'capture_image',
                },
            },
            'requestId': 'efg-456'
        })

    mock_client.assert_called_once()


def test_invoke_start_session(iot):
    connectionId = str(uuid4())
    otherConnectionId = str(uuid4())
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'expiresIn': floor(time.time()) + 60 * 1000,
            'authorized': True,
        }
    )
    connections.create(
        '123456789012',
        item={
            'connectionId': otherConnectionId,
            'managerId': connectionId,
            'expiresIn': floor(time.time()) + 60 * 1000,
            'authorized': True,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'invoke',
                'statusCode': 200,
                'body': {
                    'invokeId': 'abc-123'
                },
                'requestId': 'id'
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={
            'payload': {
                'connectionId': otherConnectionId,
                'invokeId': 'abc-123',
                'camera': 'PitsCamera1',
                'event': {
                    'name': 'recording',
                    'session': {
                        'start': True,
                    }
                }
            }
        })

    mock_client.assert_called_once()
    sessions = app_context.resolve()['sessions']
    session = sessions.get(
        '123456789012',
        'Connections',
        connectionId,
        item_id='abc-123'
    )
    assert session['invokeId'] == 'abc-123'
    assert session['connectionId'] == connectionId
    assert session['camera'] == 'PitsCamera1'


def test_invoke_stop_session(iot):
    connectionId = 'other-con-id'
    connections = app_context.resolve()['connections']
    connections.create(
        '123456789012',
        item={
            'connectionId': connectionId,
            'authorized': True,
            'manager': True,
        }
    )

    sessions = app_context.resolve()['sessions']
    sessions.create(
        '123456789012',
        'Connections',
        'other-con-id',
        item={
            'invokeId': 'abc-123',
            'connectionId': 'other-con-id',
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == connectionId
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'action': 'invoke',
                'statusCode': 200,
                'body': {
                    'invokeId': 'abc-123'
                },
                'requestId': 'id',
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId=connectionId, body={
            'payload': {
                'invokeId': 'abc-123',
                'camera': 'PitsCamera1',
                'event': {
                    'name': 'recording',
                    'session': {
                        'stop': True,
                    }
                }
            }
        })

    mock_client.assert_called_once()
    assert sessions.get(
        '123456789012',
        'Connections',
        connectionId,
        item_id='abc-123'
    ) is None


def test_list_sessions_self(iot):
    sessions = app_context.resolve()['sessions']

    session = sessions.create(
        '123456789012',
        'Connections',
        'other-con-id',
        item={
            'invokeId': '11111',
            'camera': 'PitsCamera1',
            'event': {
                'name': 'record',
                'session': {
                    'start': True
                }
            }
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "other-con-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'listSessions',
                'statusCode': 200,
                'body': {
                    'items': [
                        session
                    ],
                    'nextToken': None,
                    'connectionId': 'other-con-id',
                },
                'requestId': 'id'
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='other-con-id', body={})

    mock_client.assert_called_once()


def test_list_sessions_unauthorized(iot):
    connections = app_context.resolve()['connections']

    connections.create(
        '123456789012',
        item={
            'connectionId': 'unauthorized-id',
            'authorized': False,
            'manager': True,
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "unauthorized-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'listSessions',
                'statusCode': 401,
                'error': {
                    'code': 'AccessDenied',
                    'message': 'Connection unauthorized-id is not authorized'
                },
                'requestId': 'id'
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='unauthorized-id', body={})

    mock_client.assert_called_once()


def test_list_sessions_not_found(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-found-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'listSessions',
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection not-found-id was not found'
                },
                'requestId': 'id'
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='not-found-id', body={})

    mock_client.assert_called_once()


def test_list_sessions_not_found_other(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-found-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'listSessions',
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection other-con-id was not found'
                },
                'requestId': 'id'
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='not-found-id', body={
            'payload': {
                'connectionId': 'other-con-id',
            }
        })

    mock_client.assert_called_once()


def test_list_sessions_managed(iot):
    sessions = app_context.resolve()['sessions']
    connections = app_context.resolve()['connections']

    connections.create(
        '123456789012',
        item={
            'connectionId': 'child-con-id',
            'manager': False,
            'authorized': True,
            'managerId': 'other-con-id'
        }
    )

    session = sessions.create(
        '123456789012',
        'Connections',
        'child-con-id',
        item={
            'invokeId': '11111',
            'camera': 'PitsCamera1',
            'event': {
                'name': 'record',
                'session': {
                    'start': True
                }
            }
        }
    )

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "other-con-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'listSessions',
                'statusCode': 200,
                'body': {
                    'items': [
                        session
                    ],
                    'nextToken': None,
                    'connectionId': 'child-con-id',
                },
                'requestId': 'id'
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='other-con-id', body={
            'payload': {
                'connectionId': 'child-con-id'
            }
        })

    mock_client.assert_called_once()


def test_list_sessions_not_found_other_session(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-found-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'action': 'listSessions',
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection child-con-id was not found'
                },
                'requestId': 'id'
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='not-found-id', body={
            'payload': {
                'connectionId': 'child-con-id',
            }
        })

    mock_client.assert_called_once()
