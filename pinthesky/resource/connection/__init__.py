import logging
from ophis.globals import app_context, request
from pinthesky.database import DataConnections
from pinthesky.util import iterate_all_items
from pinthesky import api, management


logger = logging.getLogger(__name__)
app_context.inject('connections', DataConnections())


@api.routeKey('$connect')
def connect(connections):
    manager_id = request.headers.get('ManagerId', None)
    connection_id = request.request_context('connectionId')
    connections.create(
        request.account_id(),
        item={
            'connectionId': connection_id,
            'managerId': manager_id,
            'manager': manager_id is None,
        })
    print(manager_id)
    if manager_id is None:
        logger.info("Started a manager connection")

        @management.post()
        def post_manager():
            return {'body': {'connectionId': connection_id}}

        post_manager()
    else:
        logger.info(f'Started a child connection on manager {manager_id}')
        connections.create(
            request.account_id(),
            'Manager',
            manager_id,
            item={'connectionId': connection_id})

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
