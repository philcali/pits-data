from ophis.database import Repository

class DataConnections(Repository):
    def __init__(self, table=None) -> None:
        super().__init__(table=table, type="DataConnections", fields_to_keys={
            'connectionId': 'SK'
        })
