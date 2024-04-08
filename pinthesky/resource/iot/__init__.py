import boto3
import json
import logging
import os
from ophis.database import Repository, QueryParams, MAX_ITEMS
from ophis.globals import app_context, request
from pinthesky import api, management
from pinthesky.database import DataSessions
from uuid import uuid4


logger = logging.getLogger(__name__)
DATA_ENDPOINT = f'https://{os.getenv("DATA_ENDPOINT")}'


app_context.inject('sessions', DataSessions())
app_context.inject(
    'iot_data',
    boto3.client('iot-data', endpoint_url=DATA_ENDPOINT))


@api.routeKey('invoke')
def invoke(iot_data, connections, sessions):
    input = {} if request.body == "" else json.loads(request.body)
    payload = {'statusCode': 200}

    @management.post()
    def post_to_connection():
        return payload

    connection = connections.get(
        request.account_id(),
        item_id=request.request_context('connectionId'),
    )

    if connection is None or not connection['authorized']:
        payload['statusCode'] = 401
        payload['error'] = {
            'code': 'AccessDenied',
            'message': f'Connection {request.request_context("connectionId")} is not authorized',
        }
        return post_to_connection()

    def validate_input(field, obj, force=False):
        if force or field not in obj:
            payload['statusCode'] = 400
            payload['error'] = {
                'code': 'InvalidInput',
                'message': f'Input payload {field} is invalid'
            }
            return False
        return True

    for key in ['camera', 'event']:
        if not validate_input(key, input):
            return post_to_connection()

    if not validate_input('name', input['event']):
        return post_to_connection()

    session = input['event'].get('session', {
        'start': False,
        'stop': False,
    })

    if session.get('start', False) and session.get('stop', False):
        validate_input('session', input['event'], force=True)
        return post_to_connection()

    invoke_id = input.get('invokeId', str(uuid4()))
    if session.get('start', False):
        sessions.create(
            request.account_id(),
            'Connections',
            request.request_context('connectionId'),
            item={
                'invokeId': invoke_id,
                'connectionId': request.request_context('connectionId'),
                'camera': input['camera'],
                'event': input['event'],
            }
        )

    management.publish(
        iot_data=iot_data,
        thing_name=input['camera'],
        event=input['event'],
        invoke_id=invoke_id,
    )

    if session.get('stop', False):
        sessions.delete(
            request.account_id(),
            'Connections',
            request.request_context('connectionId'),
            item_id=invoke_id
        )

    payload['body'] = {'invokeId': invoke_id}

    return post_to_connection()


@api.routeKey("listSessions")
def list_sessions(connections, sessions):
    payload = {'statusCode': 200}

    @management.post()
    def post_to_connection():
        return payload

    connection_id = request.request_context('connectionId')
    input = {'connectionId': connection_id} if request.body == "" else json.loads(request.body)
    reads = [
        {
            'repository': connections,
            'id': connection_id,
        },
    ]
    if input.get('connectionId', connection_id) != connection_id:
        reads.append({
            'repository': connections,
            'id': input['connectionId'],
        })
    batches = Repository.batch_read(request.account_id(), reads=reads)
    # We'll allow a connection to list its own sessions or managed sessions
    if len(batches) == 0 or (
            (batches[-1]['manager'] and batches[-1]['connectionId'] != connection_id) or
            (not batches[-1]['manager'] and batches[-1]['managerId'] != connection_id)
    ):
        payload['statusCode'] = 404
        payload['error'] = {
            'code': 'ResourceNotFound',
            'message': f'The connection {input.get("connectionId", connection_id)} was not found',
        }
        return post_to_connection()

    if not batches[0]['authorized']:
        payload['statusCode'] = 401
        payload['error'] = {
            'code': 'AccessDenied',
            'message': f'Connection {connection_id} is not authorized'
        }
        return post_to_connection()

    try:
        resp = sessions.items(
            request.account_id(),
            'Connections',
            batches[-1]['connectionId'],
            params=QueryParams(
                limit=input.get('limit', MAX_ITEMS),
                next_token=input.get('nextToken', None),
            )
        )
        payload['body'] = {
            'items': resp.items,
            'nextToken': resp.next_token,
            'connectionId': batches[-1]['connectionId']
        }
    except Exception as e:
        logger.error(
            f"Failed to listSessions for {batches[-1]['connectionId']}:",
            exc_info=e
        )
        payload['statusCode'] = 500
        payload['error'] = {
            'code': 'InternalServerError',
            'message': str(e)
        }

    return post_to_connection()
