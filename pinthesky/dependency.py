import logging
from pinthesky.wrappers import _ContextContainer


logger = logging.getLogger(__name__)


class Context(_ContextContainer):
    def __init__(self) -> None:
        super().__init__('application', [
            'internal_scopes',
        ])

    def inject(self, name, value, scope='GLOBAL', force=False):
        if self.internal_scopes is None:
            self.internal_scopes = {}
        if scope not in self.internal_scopes:
            self.internal_scopes[scope] = {}
        if force or name not in self.internal_scopes[scope]:
            self.internal_scopes[scope][name] = value
        else:
            logger.warning(f'Trying to override {name}, use unset or force')

    def remove(self, name, scope='GLOBAL'):
        return self.internal_scopes[scope].pop(name)

    def scopes(self):
        if self.internal_scopes is None:
            return []
        return self.internal_scopes.keys()

    def keys_in_scope(self, scope):
        return self.resolve(scope).keys()

    def resolve(self, scope):
        if self.internal_scopes is None:
            return {}
        if scope not in self.internal_scopes:
            return {}
        return self.internal_scopes[scope]
