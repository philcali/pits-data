from contextvars import copy_context
from decimal import Decimal
import traceback
from pinthesky.globals import request, response, app_context
import inspect
import json
import logging
import re


logger = logging.getLogger(__name__)


class RouterEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return f'{o.normalize():f}'
        return super().default(o)


class Router:
    def __init__(self) -> None:
        self.routes = {}
        self.filters = []

    def __call__(self, event, context):
        logger.debug(f'Incoming event {event}')
        ctx = copy_context()
        self.__prepare_context(ctx, event, context)
        for filter in self.filters:
            kwargs = self.__fill_globals(filter)
            output = ctx.run(filter, **kwargs)
            if self.__is_aborted(ctx):
                return self.__dispatch_response(ctx, output, aborted=True)
        for rule, route in self.routes.items():
            method, pattern = rule.split(':', 1)
            if method == event['requestContext']['http']['method']:
                raw_path = event['requestContext']['http']['path']
                match = re.search(pattern, raw_path)
                if pattern == raw_path or match is not None:
                    logger.info(f'Found {route.__module__}.{route.__name__}')
                    output = self.__dispatch_request(
                        ctx, route, list(match.groups()))
                    return self.__dispatch_response(ctx, output)
        return {
            'statusCode': 404,
            'headers': {'content-type': 'application/json'},
            'body': '{"message": "Resource not found"}'
        }

    def __dispatch_response(self, ctx, output, aborted=False):
        def format_output(real_out):
            if isinstance(real_out, dict):
                real_out = json.dumps(real_out, cls=RouterEncoder)
                if 'content-type' not in response.headers:
                    response.headers['content-type'] = 'application/json'
            elif isinstance(real_out, str):
                if 'content-type' not in response.headers:
                    response.headers['content-type'] = 'text/plain'
            b = real_out if real_out is not None else response.body
            response.headers['content-length'] = 0 if b is None else len(b)
            if not aborted and b is None and response.status_code == 200:
                response.status_code = 204
            return {
                'statusCode': response.status_code,
                'body': b,
                'headers': response.headers
            }
        return ctx.run(format_output, output)

    def __fill_globals(self, route):
        kwargs = {}
        sig = inspect.signature(route)
        for key, value in app_context.resolve('GLOBAL').items():
            if key in sig.parameters:
                kwargs[key] = value
        return kwargs

    def __is_aborted(self, ctx):
        def obtain_aborted():
            return response.is_aborted()
        return ctx.run(obtain_aborted)

    def __fail(self, ctx):
        def fail_response():
            response.status_code = 500
        ctx.run(fail_response)

    def __dispatch_request(self, ctx, route, path_values):
        kwargs = self.__fill_globals(route)
        for index in range(0, len(route.path_names)):
            kwargs[route.path_names[index]] = path_values[index]
        try:
            return ctx.run(route, **kwargs)
        except Exception as e:
            trace = ''.join(traceback.format_exception(
                e,
                value=e,
                tb=e.__traceback__))
            logger.error(f"Failed to run {route.__name__}:\n{trace}")
            self.__fail(ctx)
            return {
                'message': 'Internal server error'
            }

    def __prepare_context(self, ctx, event, context):
        def fill_values():
            qparams = 'queryStringParameters'
            response.status_code = 200
            response.headers = {}
            response.abort = False
            request.cookies = event['cookies'] if 'cookies' in event else {}
            request.headers = event['headers']
            request.queryparams = event[qparams] if qparams in event else {}
            request.body = event['body'] if 'body' in event else None
            request.event = event
            request.context = context
        ctx.run(fill_values)

    def filter(self):
        def wrapper(func):
            self.filters.append(func)
            return func
        return wrapper

    def routeKey(self, routeKey):
        def wrapper(func):
            def filter_func(**kwargs):
                if request.event['routeKey'] == routeKey:
                    response.break_continuation()
                    func(**kwargs)
            self.filters.append(filter_func)
        return wrapper

    def route(self, path, methods=["GET"]):
        def wrapper(func):
            for method in methods:
                path_parts = []

                def replace_update(obj):
                    path_parts.append(obj.group(0).lstrip(':'))
                    return '([^/]+)'
                new_path = '^' + re.sub(':[^/]+', replace_update, path) + '$'
                rule = ':'.join([method.upper(), new_path])
                if rule in self.routes:
                    logger.warn(f'Rule {rule} is already in use. Overwriting.')
                setattr(func, 'path_names', path_parts)
                self.routes[rule] = func
            return func
        return wrapper
