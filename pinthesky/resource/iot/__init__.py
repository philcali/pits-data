import boto3
import json
import os
from ophis.globals import app_context, request
from pinthesky import api, management
from pinthesky.database import DataSessions
from uuid import uuid4


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
