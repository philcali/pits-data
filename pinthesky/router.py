from boto3.dynamodb.conditions import Key
import boto3
import os
import json


ddb = boto3.resource('dynamodb')


def connect(event, context):
    print(f'Event content {event}')
    print(f'Event context {context}')
    table = ddb.Table(os.getenv('TABLE_NAME'))
    account = os.getenv('ACCOUNT_ID')
    table.put_item(Item={
        'PK': f'DataConnections:{account}',
        'SK': event['requestContext']['connectionId'],
        'connectionId': event['requestContext']['connectionId'],
    })
    return {
        'statusCode': 200
    }


def disconnect(event, context):
    print(f'Event content {event}')
    print(f'Event context {context}')
    table = ddb.Table(os.getenv('TABLE_NAME'))
    account = os.getenv('ACCOUNT_ID')
    table.delete_item(Key={
        'PK': f'DataConnections:{account}',
        'SK': event['requestContext']['connectionId'],
    })
    return {
        'statusCode': 200
    }


def default(event, context):
    print(f'Event content {event}')
    print(f'Event context {context}')
    management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'{event["requestContext"]["domainName"]}/{event["requestContext"]["stage"]}')
    management.post_to_connection(
        ConnectionId=event["requestContext"]["connectionId"],
        Data=f'Use the sendMessage route to send a message.'.encode(encoding='utf-8'),
    )
    return {
        'statusCode': 200
    }


def send_message(event, context):
    print(f'Event content {event}')
    print(f'Event context {context}')
    table = ddb.Table(os.getenv('TABLE_NAME'))
    account = os.getenv('ACCOUNT_ID')
    management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'{event["requestContext"]["domainName"]}/{event["requestContext"]["stage"]}')
    resp = table.query(KeyConditionExpression=Key("PK").eq(f'DataConnections:{account}'))
    payload = json.loads(event['body'])
    for item in resp["Items"]:
        management.post_to_connection(
            ConnectionId=item['connectionId'],
            Data=payload['message'].encode(encoding='utf-8')
        )
    return {
        'statusCode': 200
    }
