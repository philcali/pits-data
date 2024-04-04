import boto3
import os
from ophis.globals import app_context

ddb = boto3.resource('dynamodb')

app_context.inject('dynamodb', ddb)
app_context.inject('table', ddb.Table(os.getenv('TABLE_NAME', 'Pits')))
