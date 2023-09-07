from pyramid.security import NO_PERMISSION_REQUIRED

from riskmatrix.route_factories import organization_factory

from .forbidden import forbidden_view
from .home import home_view
from .login import login_view
from .logout import logout_view
from .organization import organization_view


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.config import Configurator


def includeme(config: 'Configurator') -> None:

    config.add_static_view(
        'static',
        'riskmatrix:static',
        cache_max_age=3600
    )
    config.add_forbidden_view(forbidden_view)

    config.add_route('home', '/')
    config.add_view(home_view, route_name='home')

    config.add_route('login', '/login')
    config.add_view(
        login_view,
        route_name='login',
        renderer='templates/login.pt',
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED
    )

    config.add_route('logout', '/logout')
    config.add_view(logout_view, route_name='logout')

    config.add_route(
        'organization',
        '/organization',
        factory=organization_factory
    )
    config.add_view(
        organization_view,
        route_name='organization',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        organization_view,
        route_name='organization',
        renderer='json',
        xhr=True
    )
