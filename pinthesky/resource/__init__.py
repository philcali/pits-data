import boto3
import os
import json
from pinthesky import api
from pinthesky.database import DataConnections
from ophis.globals import app_context, request
from ophis.database import QueryParams

ddb = boto3.resource('dynamodb')

app_context.inject('dynamodb', ddb)
app_context.inject('table', ddb.Table(os.getenv('TABLE_NAME')))
app_context.inject('connections', DataConnections())


@api.routeKey('$connect')
def connect(connections):
    account = request.account_id()
    connections.create(
        account,
        item={'connectionId': request.request_context('connectionId')})


@api.routeKey('$disconnect')
def disconnect(connections):
    account = request.account_id()
    connections.delete(account, item_id=request.request_context('connectionId'))


@api.routeKey('$default')
def default():
    management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{request.request_context("domainName")}/{request.request_context("stage")}')
    management.post_to_connection(
        ConnectionId=request.request_context('connectionId'),
        Data=f'Use the sendMessage route to send a message.'.encode(encoding='utf-8'),
    )


@api.routeKey('sendMessage')
def send_message(connections):
    management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{request.request_context("domainName")}/{request.request_context("stage")}')
    payload = json.loads(request.body)
    truncated = True
    next_token = None
    while truncated:
        resp = connections.items(
            request.account_id(),
            params=QueryParams(next_token=next_token))
        for item in resp.items:
            management.post_to_connection(
                ConnectionId=item['connectionId'],
                Data=payload['message'].encode(encoding='utf-8')
            )
        next_token = resp.next_token
        truncated = next_token is not None
