from ophis import set_stream_logger
from pinthesky import api, management
from pinthesky.resource import inject, connection, iot, auth


for module in [inject, connection, iot, auth]:
    set_stream_logger(module.__name__)


@api.routeKey('$default')
@management.post()
def default():
    """
    This fallback handler is used for connections to discover
    available actions surfaced by the websocket server.
    """
    routeKeys = []
    for filter in api.filters:
        if hasattr(filter, 'routeKey'):
            route_key = getattr(filter, 'routeKey')
            if "$" not in route_key:
                routeKeys.append(route_key)
    return {
        'statusCode': 404,
        'error': {
            'code': 'ResourceNotFound',
            'message': 'Resource not found',
        },
        'body': {
            'availableActions': routeKeys,
        },
    }
