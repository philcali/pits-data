import boto3
import json
import logging
import os
from ophis.database import QueryParams, MAX_ITEMS
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
def invoke(iot_data, sessions):
    input = json.loads(request.body)
    payload = {'statusCode': 200}

    @management.post()
    def post_to_connection():
        return payload

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
    connection = connections.get(
        request.account_id(),
        item_id=input.get('connectionId', connection_id)
    )
    # We'll allow a connection to list its own sessions or managed sessions
    if connection is None or (
            (connection['manager'] and connection['connectionId'] != connection_id) or
            (not connection['manager'] and connection['manager_id'] != connection_id)
    ):
        payload['statusCode'] = 404
        payload['error'] = {
            'code': 'ResourceNotFound',
            'message': f'The connection {input.get("connectionId", connection_id)} was not found',
        }
        return post_to_connection()

    try:
        resp = sessions.items(
            request.account_id(),
            'Connections',
            connection['connectionId'],
            params=QueryParams(
                limit=input.get('limit', MAX_ITEMS),
                next_token=input.get('nextToken', None),
            )
        )
        payload['body'] = {
            'items': resp.items,
            'nextToken': resp.next_token,
            'connectionId': connection['connectionId']
        }
    except Exception as e:
        logger.error(
            f"Failed to listSessions for {connection['connectionId']}:",
            exc_info=e
        )
        payload['statusCode'] = 500
        payload['error'] = {
            'code': 'InternalServerError',
            'message': str(e)
        }

    return post_to_connection()
