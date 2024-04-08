from ophis import set_stream_logger
from pinthesky import api, management
from pinthesky.resource import inject, connection, iot, auth


for module in [inject, connection, iot, auth]:
    set_stream_logger(module.__name__)


@api.routeKey('$default')
@management.post()
def default():
    return {
        'statusCode': 404,
        'error': {
            'code': 'ResourceNotFound',
            'message': 'Resource not found',
        },
        'body': {
            'availableActions': [
                'login',
                'invoke',
                'listSessions',
            ]
        },
    }
