import logging
from ophis.globals import app_context, request
from pinthesky.database import DataConnections
from pinthesky.util import iterate_all_items
from pinthesky import api, management


logger = logging.getLogger(__name__)
app_context.inject('connections', DataConnections())


@api.routeKey('$connect')
def connect(connections):

    logger.info(f'Event: {request.event}')

    @management.post()
    def post_error(reason, status_code=400, code='InvalidInput'):
        return {
            'statusCode': status_code,
            'error': {
                'code': code,
                'message': reason,
            }
        }

    protocol = request.headers.get('Sec-Websocket-Protocol', None)
    if protocol is None or protocol not in ['manager', 'child']:
        return post_error('Invalid subprotocol. Expected manager or child')

    manager_id = request.headers.get('ManagerId', None)
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
            **expiresIn,
        })

    if protocol == 'manager':
        logger.info("Started a manager connection")

        @management.post()
        def post_manager():
            return {'body': {'connectionId': connection_id}}

        post_manager()
    elif protocol == 'child' and manager_id is not None:
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

        post_child_to_manager()


@api.routeKey('$disconnect')
def disconnect(iot_data, connections, sessions):
    connection = connections.get(
        request.account_id(),
        item_id=request.request_context('connectionId'),
    )
    if connection is not None and 'managerId' in connection:
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
