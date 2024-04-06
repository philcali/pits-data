import boto3
import json
from ophis.globals import app_context
from unittest.mock import MagicMock, patch


def test_invoke_validate(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload camera is invalid',
                },
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", body={})

    mock_client.assert_called_once()


def test_invoke_validate_event(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload name is invalid',
                },
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", body={
            'camera': 'PitsCamera1',
            'event': {
            }
        })

    mock_client.assert_called_once()


def test_invoke_validate_session(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 400,
                'error': {
                    'code': 'InvalidInput',
                    'message': 'Input payload session is invalid',
                },
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", body={
            'camera': 'PitsCamera1',
            'event': {
                'name': 'recording',
                'session': {
                    'start': True,
                    'stop': True
                }
            }
        })

    mock_client.assert_called_once()


def test_invoke_non_session(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 200,
                'body': {
                    'invokeId': 'abc-123'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", body={
            'invokeId': 'abc-123',
            'camera': 'PitsCamera1',
            'event': {
                'name': 'capture_image',
            }
        })

    mock_client.assert_called_once()


def test_invoke_start_session(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "$connectionId"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 200,
                'body': {
                    'invokeId': 'abc-123'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", body={
            'invokeId': 'abc-123',
            'camera': 'PitsCamera1',
            'event': {
                'name': 'recording',
                'session': {
                    'start': True,
                }
            }
        })

    mock_client.assert_called_once()
    sessions = app_context.resolve()['sessions']
    session = sessions.get(
        '123456789012',
        'Connections',
        '$connectionId',
        item_id='abc-123'
    )
    assert session['invokeId'] == 'abc-123'
    assert session['connectionId'] == '$connectionId'
    assert session['camera'] == 'PitsCamera1'


def test_invoke_stop_session(iot):

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
        assert ConnectionId == "other-con-id"
        assert Data.decode('utf-8') == json.dumps({
            'response': {
                'statusCode': 200,
                'body': {
                    'invokeId': 'abc-123'
                }
            }
        })

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="invoke", connectionId='other-con-id', body={
            'invokeId': 'abc-123',
            'camera': 'PitsCamera1',
            'event': {
                'name': 'recording',
                'session': {
                    'stop': True,
                }
            }
        })

    mock_client.assert_called_once()
    assert sessions.get(
        '123456789012',
        'Connections',
        'other-con-id',
        item_id='abc-123'
    ) is None


def test_list_sessions_self(iot):
    sessions = app_context.resolve()['sessions']
    connections = app_context.resolve()['connections']

    connections.create(
        '123456789012',
        item={
            'connectionId': 'other-con-id',
            'manager': True,
        }
    )

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
                'statusCode': 200,
                'body': {
                    'items': [
                        session
                    ],
                    'nextToken': None,
                    'connectionId': 'other-con-id',
                }
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='other-con-id', body={})

    mock_client.assert_called_once()


def test_list_sessions_not_found(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-found-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection not-found-id was not found'
                }
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
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection other-con-id was not found'
                }
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='not-found-id', body={
            'connectionId': 'other-con-id',
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
            'manager_id': 'other-con-id'
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
                'statusCode': 200,
                'body': {
                    'items': [
                        session
                    ],
                    'nextToken': None,
                    'connectionId': 'child-con-id',
                }
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='other-con-id', body={
            'connectionId': 'child-con-id'
        })

    mock_client.assert_called_once()


def test_list_sessions_not_found_other_session(iot):

    def post_to_connection(ConnectionId, Data):
        assert ConnectionId == "not-found-id"
        assert json.loads(Data.decode('utf-8')) == {
            'response': {
                'statusCode': 404,
                'error': {
                    'code': 'ResourceNotFound',
                    'message': 'The connection child-con-id was not found'
                }
            }
        }

    management = MagicMock()
    management.post_to_connection = post_to_connection
    with patch.object(boto3, 'client', return_value=management) as mock_client:
        iot(routeKey="listSessions", connectionId='not-found-id', body={
            'connectionId': 'child-con-id',
        })

    mock_client.assert_called_once()
