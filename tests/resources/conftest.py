import pytest
from ophis.globals import app_context
from resources import Resources
from unittest.mock import MagicMock


@pytest.fixture(scope="module")
def connections(table):
    iot_data = MagicMock()
    app_context.inject('iot_data', iot_data, force=True)

    assert table.name == 'Pits'
    from pinthesky.resource import connection

    return Resources(connection)


@pytest.fixture(scope="module")
def iot(table):
    iot_data = MagicMock()
    app_context.inject('iot_data', iot_data, force=True)

    assert table.name == 'Pits'
    from pinthesky.resource import iot

    return Resources(iot)
