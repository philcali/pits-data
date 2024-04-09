import boto3
import json
import logging
import os
from botocore.client import ClientError
from ophis.database import QueryParams
from ophis.globals import request
from uuid import uuid4


logger = logging.getLogger(__name__)


def iterate_all_items(repo, *args):
    next_token = None
    truncated = True
    while truncated:
        resp = repo.items(
            *args,
            params=QueryParams(next_token=next_token))
        for item in resp.items:
            yield item
        next_token = resp.next_token
        truncated = next_token is not None


class ManagementWrapper:

    def connection_url(self):
        override = os.getenv('SERVICE_DOMAIN')
        return override if override != '' else f'{request.request_context("domainName")}/{request.request_context("stage")}'

    def client(self):
        return boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=f'https://{self.connection_url()}',
        )

    def publish(self, iot_data, thing_name, event, invoke_id=None):
        session_id = invoke_id if invoke_id is not None else str(uuid4())
        iot_data.publish(
            topic=f'pinthesky/events/{thing_name}/input',
            payload=json.dumps({
                'name': event['name'],
                'context': {
                    **event.get('context', {}),
                    **event.get('session', {}),
                    'connection': {
                        'id': request.request_context('connectionId'),
                        'invoke_id': session_id
                    }
                }
            }).encode('utf-8')
        )
        return session_id

    def post(self, connectionId=None):
        def inner(func):

            # TODO: fix the wrapper
            def wrapper(*args, **kwargs):
                management = self.client()
                conId = connectionId if connectionId is not None else request.request_context('connectionId')
                template = {
                    'action': request.request_context('routeKey'),
                    'statusCode': 200,
                }
                try:
                    requestId = request.request_context("requestId")
                    try:
                        requestId = json.loads(request.body).get("requestId", requestId)
                    except Exception as e:
                        logger.warning(
                            "Failed to parse input for request ID:",
                            exc_info=e
                        )
                    payload = func(*args, **kwargs)
                    template = {**template, **payload, 'requestId': requestId}
                except Exception as e:
                    logger.error(f'Failed to create body for {conId}')
                    template['statusCode'] = 500
                    template['error'] = {
                        'code': 500,
                        'message': str(e),
                    }

                management.post_to_connection(
                    ConnectionId=conId,
                    Data=json.dumps({'response': template}).encode('utf-8'),
                )

            return wrapper

        return inner

    def close_manager(self, connections):
        client = self.client()
        args = [
            request.account_id(),
            'Manager',
            request.request_context('connectionId'),
        ]
        for connection in iterate_all_items(connections, *args):
            try:
                client.delete_connection(
                    ConnectionId=connection['connectionId']
                )
            except ClientError as e:
                logger.error(
                    f'Failed to delete connection {connection["connectionId"]}',
                    exc_info=e
                )
        connections.delete(
            request.account_id(),
            item_id=request.request_context('connectionId')
        )
