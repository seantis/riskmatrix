from markupsafe import Markup

from riskmatrix.i18n import _

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable
    from pyramid.interfaces import IRequest

    from riskmatrix.types import RenderData


class NavbarEntry:

    __slots__ = ('title', 'url', 'active')

    title:  str
    url:    str
    active: bool

    def __init__(
        self,
        request: 'IRequest',
        title:   str,
        url:     str,
        active:  'Callable[[IRequest, str], bool] | None' = None
    ):
        self.title = title
        self.url = url

        if active is None:
            self.active = request.path_url == url
        else:
            self.active = active(request, url)

    def __call__(self) -> str:
        item_class = 'nav-item'
        link_class = 'nav-link'
        current = ''
        if self.active:
            item_class += ' active'
            link_class += ' active'
            current = Markup(' aria-current="page"')
        return Markup(
            '<li class="{item_class}">'
            '<a class="{link_class}" href="{url}"{current}>{title}</a>'
            '</li>'
        ).format(
            url=self.url,
            title=self.title,
            item_class=item_class,
            link_class=link_class,
            current=current,
        )

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()


def navbar(context: object, request: 'IRequest') -> 'RenderData':
    return {
        'entries': [
            NavbarEntry(
                request,
                _('Risk Catalog'),
                request.route_url('risk_catalog'),
                lambda request, url: request.path_url.startswith(request.route_url('risk_catalog'))
            ),
            NavbarEntry(
                request,
                _('Assets'),
                request.route_url('assets')
            ),
            NavbarEntry(
                request,
                _('Risk Assessment'),
                request.route_url('assessment'),
                lambda request, url: request.show_steps,
            ),
            NavbarEntry(
                request,
                _('Organization'),
                request.route_url('organization')
            ),
        ]
    }
