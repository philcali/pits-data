import logging
from ophis import set_stream_logger
from ophis.router import Router
from pinthesky.util import ManagementWrapper


logging.getLogger('pinthesky').addHandler(logging.NullHandler())
set_stream_logger('pinthesky')

api = Router()
management = ManagementWrapper()
