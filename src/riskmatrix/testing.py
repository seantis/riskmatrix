import pyramid.testing as testing
from webob.acceptparse import accept_language_property
from webob.multidict import MultiDict
from zope.interface.verify import verifyClass

from riskmatrix.flash import MessageQueue
from riskmatrix.i18n import _
from riskmatrix.security import authenticated_user


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from zope.interface import Interface

    from riskmatrix.models import User


class DummyRequest(testing.DummyRequest):

    accept_language = accept_language_property()

    def __init__(
        self,
        params:   MultiDict[str, str] | None = None,
        environ:  dict[str, Any] | None = None,
        headers:  dict[str, str] | None = None,
        path:     str = '/',
        cookies:  dict[str, str] | None = None,
        post:     MultiDict[str, str] | None = None,
        **kwargs: Any
    ):

        params = params if params else MultiDict()
        kwargs.setdefault('is_xhr', False)
        kwargs.setdefault('client_addr', '127.0.0.1')

        testing.DummyRequest.__init__(
            self, params, environ, headers, path, cookies, post, **kwargs
        )
        self.messages = MessageQueue(self)
        self.exception = None

    @property
    def user(self) -> 'User | None':
        return authenticated_user(self)


def verify_interface(klass: type[object], interface: 'Interface') -> None:
    assert interface.implementedBy(klass)  # type: ignore
    assert verifyClass(interface, klass)


# translation strings used for testing
_('Just a test')
_('<b>bold</b>', markup=True)
