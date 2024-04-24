import logging
import json
from ophis.globals import app_context, request, response
from pinthesky.database import DataConnections
from pinthesky.util import iterate_all_items
from pinthesky import api, management


logger = logging.getLogger(__name__)
app_context.inject('connections', DataConnections())


@api.routeKey('$connect')
def connect(connections):
    protocol = request.headers.get('Sec-WebSocket-Protocol', None)
    if protocol is None or protocol not in ['manager', 'session']:
        response.status_code = 400
        return {
            'body': {
                'message': f'Invalid protocol: {protocol}'
            }
        }

    manager_id = request.headers.get(
        'ManagerId',
        request.queryparams.get('ManagerId', None),
    )
    connection_id = request.request_context('connectionId')
    expiresIn = {}
    if 'exp' in request.authorizer():
        expiresIn['expiresIn'] = request.authorizer()['exp']
    connections.create(
        request.account_id(),
        item={
            'connectionId': connection_id,
            'managerId': manager_id,
            'manager': manager_id is None,
            'authorized': 'sub' in request.authorizer(),
            'claims': request.authorizer(),
            'managementEndpoint': f'https://{management.connection_url()}',
            **expiresIn,
        })

    if protocol == 'manager':
        logger.info("Started a manager connection")
        response.headers['Sec-WebSocket-Protocol'] = 'manager'
        return {'body': {'connectionId': connection_id}}
    elif protocol == 'session' and manager_id is not None:
        logger.info(f'Started a child connection on manager {manager_id}')
        connections.create(
            request.account_id(),
            'Manager',
            manager_id,
            item={
                'connectionId': connection_id,
                **expiresIn,
            })

        @management.post(connectionId=manager_id)
        def post_child_to_manager():
            return {'body': {'connectionId': connection_id}}

        response.headers['Sec-WebSocket-Protocol'] = 'session'
        post_child_to_manager()


@api.routeKey('$disconnect')
def disconnect(iot_data, connections, sessions):
    connection = connections.get(
        request.account_id(),
        item_id=request.request_context('connectionId'),
    )
    if connection is not None and connection.get('managerId') is not None:
        logger.info(f'Removing session tied to {connection["managerId"]}')
        connections.delete(
            request.account_id(),
            'Manager',
            connection['managerId'],
            item_id=request.request_context('connectionId'),
        )
    management.close_manager(connections)
    args = [
        request.account_id(),
        'Connections',
        request.request_context('connectionId'),
    ]
    for session in iterate_all_items(sessions, *args):
        sessions.delete(*args, item_id=session['invokeId'])
        management.publish(
            iot_data=iot_data,
            thing_name=session['camera'],
            event=session['event'],
            invoke_id=session['invokeId'],
        )


@api.routeKey('status')
def status(connections):
    connectionId = request.request_context('connectionId')
    input = json.loads(request.body).get('payload', {'connectionId': connectionId})
    connection = connections.get(
        request.account_id(),
        item_id=input.get('connectionId', connectionId),
    )
    payload = {'statusCode': 200}
    if connection is None or (connectionId != connection['connectionId'] and connection.get('managerId') != connectionId):
        payload['statusCode'] = 404
        payload['error'] = {
            'code': 'ResourceNotFound',
            'message': f'The connection {input.get("connectionId", connectionId)} was not found'
        }
    elif not connection.get('authorized', False):
        payload['statusCode'] = 401
        payload['error'] = {
            'code': 'Unauthorized',
            'message': f'The connection {input.get("connectionId", connectionId)} is not authorized'
        }
    else:
        payload['body'] = connection

    @management.post()
    def post_status():
        return payload

    return post_status()
