from asyncio.log import logger
from decimal import Decimal
from math import floor
from time import time
from collections import namedtuple
from boto3.dynamodb.conditions import Key, And
from botocore.exceptions import ClientError
from pinthesky.exception import ConflictException, NotFoundException
from pinthesky.globals import app_context
from pinthesky.token import EncryptedTokenMarshaller


MAX_ITEMS = 100
CON_CHECK_CODE = 'ConditionalCheckFailedException'

SortFilter = namedtuple(
    'SortFilter',
    field_names=['name', 'method', 'values'])
QueryParams = namedtuple(
    'QueryParams',
    field_names=['limit', 'next_token', 'sort_filters', 'sort_ascending'],
    defaults=[MAX_ITEMS, None, [], True])
QueryResults = namedtuple(
    'QueryResults',
    field_names=['items', 'next_token'],
    defaults=[[], None])


class Repository():
    def __init__(
            self,
            type,
            table=None,
            fields_to_keys={},
            token_marshaller=EncryptedTokenMarshaller()) -> None:
        resolved = app_context.resolve('GLOBAL')
        self.table = table if table is not None else resolved['table']
        self.type = type
        self.fields_to_keys = fields_to_keys
        self.tokens = token_marshaller

    def batch_read(*args, reads, ddb=None, table=None):
        if table is None:
            table = app_context.resolve('GLOBAL')['table']
        if ddb is None:
            ddb = app_context.resolve('GLOBAL')['dynamodb']
        params = {table.name: {'Keys': []}}
        lookups = {}
        for entry in reads:
            if 'repository' not in entry or 'id' not in entry:
                logger.warn(f'Read skipped to missing fields: {entry}')
                continue
            keys = list(args)
            if 'parent_ids' in entry:
                for parent_id in entry.pop('parent_ids'):
                    keys.append(parent_id)
            key = {
                'PK': entry['repository'].make_hash_key(*keys),
                'SK': entry['id']
            }
            params[table.name]['Keys'].append(key)
            lookups[key['PK'] + ':' + key['SK']] = entry['repository']
        resp = ddb.batch_get_item(RequestItems=params)
        return [
            lookups[item['PK'] + ':' + item['SK']].prune_dto(item)
            for item in resp['Responses'][table.name]
        ]

    def batch_write(*args, updates, table=None):
        if table is None:
            table = app_context.resolve('GLOBAL')['table']
        with table.batch_writer() as batch:
            for update in updates:
                if 'repository' not in update or 'item' not in update:
                    logger.warn(f'Update skipped to missing fields: {update}')
                    continue
                keys = list(args)
                if 'parent_ids' in update:
                    for parent_id in update.pop('parent_ids'):
                        keys.append(parent_id)
                dto = update['repository'].make_dto(
                    *keys,
                    item=update['item'],
                    time_fields=['create', 'update'])
                if update.get("delete", False):
                    batch.delete_item(Key={'PK': dto['PK'], 'SK': dto['SK']})
                else:
                    batch.put_item(Item=dto)

    def prune_dto(self, original):
        if original is None:
            return None
        rval = {}
        for key, value in original.items():
            if key in ['PK', 'SK', 'GS1-PK']:
                continue
            if type(value) is Decimal:
                value = int(value)
            rval[key] = value
        return rval

    def make_dto(self, *args, item, time_fields=['create', 'update']):
        new_item = {
            'PK': self.make_hash_key(*args)
        }
        for key, value in item.items():
            new_item[key] = value
        for key, value in self.fields_to_keys.items():
            if key not in item:
                raise Exception(f'The {self.type} item needs a {key} field')
            new_item[value] = item[key]
        for time_field in time_fields:
            if f'{time_field}Time' not in item:
                new_item[f'{time_field}Time'] = int(floor(time()))
        return new_item

    def __encrypt_token(self, hash_key, res):
        return self.tokens.encrypt(
            hash_key=hash_key,
            header=':'.join([self.type, 'next_token']),
            last_key=res.get('LastEvaluatedKey', None))

    def make_hash_key(self, *args):
        return ":".join([self.type] + list(args))

    def __list(self, *args, **kwargs):
        hash_key = self.make_hash_key(*args)
        normal_key = 'PK'
        q_params = {'ScanIndexForward': kwargs['params'].sort_ascending}
        if 'index_name' in kwargs:
            q_params['IndexName'] = kwargs['index_name']
            normal_key = f'{kwargs["index_name"]}-PK'
        key_cond = Key(normal_key).eq(hash_key)
        for f in kwargs['params'].sort_filters:
            sk = f.name
            if f.name in self.fields_to_keys:
                sk = self.fields_to_keys[f.name]
            key_cond = And(key_cond, getattr(Key(sk), f.method)(*f.values))
        q_params['KeyConditionExpression'] = key_cond
        q_params['Limit'] = kwargs['params'].limit
        last_key = self.tokens.decrypt(
            hash_key=hash_key,
            header=':'.join([self.type, 'next_token']),
            next_token=kwargs['params'].next_token)
        if last_key is not None:
            q_params['ExclusiveStartKey'] = last_key
        response = self.table.query(**q_params)
        items = map(
            self.prune_dto,
            response['Items'] if 'Items' in response else [])
        return QueryResults(
            items=list(items),
            next_token=self.__encrypt_token(hash_key, response)
        )

    def items(self, *args, params=QueryParams()):
        kwargs = {'params': params}
        return self.__list(*args, **kwargs)

    def items_index(self, *args, index_name, params=QueryParams()):
        kwargs = {'params': params, 'index_name': index_name}
        return self.__list(*args, **kwargs)

    def create(self, *args, item):
        new_item = self.make_dto(*args, item=item)
        exp = "attribute_not_exists(PK) and attribute_not_exists(SK)"
        try:
            self.table.put_item(
                Item=new_item,
                ConditionExpression=exp
            )
        except ClientError as e:
            if e.response['Error']['Code'] == CON_CHECK_CODE:
                raise ConflictException(
                    f'This {self.type} item already exists.')
            raise e
        return self.prune_dto(new_item)

    def update(self, *args, item, fields_to_remove=[]):
        new_item = self.make_dto(*args, item=item, time_fields=['update'])
        condition = "attribute_exists(PK) and attribute_exists(SK)"
        update_exp = []
        remove_exp = []
        update_names = {}
        update_values = {}
        for key, value in new_item.items():
            if key in ['PK', 'SK'] or key in self.fields_to_keys:
                continue
            update_names[f'#{key}'] = key
            update_values[f':{key}'] = value
            update_exp.append(f'#{key} = :{key}')
        for field in fields_to_remove:
            update_names[f'#{field}'] = field
            remove_exp.append(f'#{field}')
        try:
            expression = []
            if len(update_exp) > 0:
                expression.append(f'SET {", ".join(update_exp)}')
            if len(remove_exp) > 0:
                expression.append(f'REMOVE {", ".join(remove_exp)}')
            response = self.table.update_item(
                Key={
                    'PK': new_item['PK'],
                    'SK': new_item['SK']
                },
                ConditionExpression=condition,
                UpdateExpression=" AND ".join(expression),
                ExpressionAttributeNames=update_names,
                ExpressionAttributeValues=update_values,
                ReturnValues='ALL_NEW',
            )
            return self.prune_dto(response['Attributes'])
        except ClientError as e:
            if e.response['Error']['Code'] == CON_CHECK_CODE:
                raise NotFoundException(f'The {self.type} item not exist.')
            raise e

    def delete(self, *args, item_id):
        self.table.delete_item(
            Key={
                'PK': self.make_hash_key(*args),
                'SK': item_id
            }
        )

    def get(self, *args, item_id):
        response = self.table.get_item(
            Key={
                'PK': self.make_hash_key(*args),
                'SK': item_id
            }
        )
        return self.prune_dto(response.get('Item', None))


class DataConnections(Repository):
    def __init__(self, table=None) -> None:
        super().__init__(table=table, type="DataConnections", fields_to_keys={
            'connectionId': 'SK'
        })
