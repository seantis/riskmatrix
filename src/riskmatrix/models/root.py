from pyramid.authorization import Allow
from pyramid.authorization import Authenticated


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.types import ACL


class Root:
    def __acl__(self) -> list['ACL']:
        return [(Allow, Authenticated, ['view'])]
