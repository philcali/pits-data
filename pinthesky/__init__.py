import logging
import os
from ophis import set_stream_logger
from ophis.router import Router
from pinthesky.util import ManagementWrapper


logging.getLogger('pinthesky').addHandler(logging.NullHandler())
set_stream_logger('ophis', level=os.getenv('LOG_LEVEL', 'INFO'))
set_stream_logger('pinthesky', level=os.getenv('LOG_LEVEL', 'INFO'))

api = Router()
management = ManagementWrapper()
