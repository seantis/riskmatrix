from pyramid.security import NO_PERMISSION_REQUIRED

from riskmatrix.route_factories import asset_factory
from riskmatrix.route_factories import organization_factory
from riskmatrix.route_factories import risk_factory
from riskmatrix.route_factories import risk_assessment_factory
from riskmatrix.route_factories import risk_catalog_factory

from .asset import assets_view
from .asset import delete_asset_view
from .asset import edit_asset_view
from .forbidden import forbidden_view
from .home import home_view
from .login import login_view
from .logout import logout_view
from .organization import organization_view
from .risk import delete_risk_view
from .risk import edit_risk_view
from .risk import risks_view
from .risk_assessment import assess_impact_view
from .risk_assessment import assess_likelihood_view
from .risk_assessment import assessment_view
from .risk_assessment import edit_assessment_view
from .risk_assessment import generate_risk_matrix_view
from .risk_assessment import set_impact_view
from .risk_assessment import set_likelihood_view
from .risk_catalog import delete_risk_catalog_view
from .risk_catalog import edit_risk_catalog_view
from .risk_catalog import risk_catalog_view


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
        request_method='POST',
        xhr=True
    )

    # Asset views

    config.add_route(
        'assets',
        '/assets',
        factory=organization_factory
    )
    config.add_view(
        assets_view,
        route_name='assets',
        renderer='templates/table.pt',
    )

    config.add_route(
        'add_asset',
        '/assets/add',
        factory=organization_factory
    )
    config.add_view(
        edit_asset_view,
        route_name='add_asset',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_asset_view,
        route_name='add_asset',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'edit_asset',
        '/assets/{id}/edit',
        factory=asset_factory
    )
    config.add_view(
        edit_asset_view,
        route_name='edit_asset',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_asset_view,
        route_name='edit_asset',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_asset',
        '/assets/{id}/delete',
        factory=asset_factory
    )
    config.add_view(
        delete_asset_view,
        route_name='delete_asset',
        xhr=False
    )
    config.add_view(
        delete_asset_view,
        route_name='delete_asset',
        renderer='json',
        request_method='DELETE',
        xhr=True
    )

    # Risk catalog views

    config.add_route(
        'risk_catalog',
        '/risk_catalog',
        factory=organization_factory
    )
    config.add_view(
        risk_catalog_view,
        route_name='risk_catalog',
        renderer='templates/table.pt',
    )

    config.add_route(
        'add_catalog',
        '/risks_catalog/add',
        factory=organization_factory
    )
    config.add_view(
        edit_risk_catalog_view,
        route_name='add_catalog',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_risk_catalog_view,
        route_name='add_catalog',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'edit_catalog',
        '/risk_catalog/{id}/edit',
        factory=risk_catalog_factory
    )
    config.add_view(
        edit_risk_catalog_view,
        route_name='edit_catalog',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_risk_catalog_view,
        route_name='edit_catalog',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_catalog',
        '/risk_catalog/{id}/delete',
        factory=risk_catalog_factory
    )
    config.add_view(
        delete_risk_catalog_view,
        route_name='delete_catalog',
        xhr=False
    )
    config.add_view(
        delete_risk_catalog_view,
        route_name='delete_catalog',
        renderer='json',
        request_method='DELETE',
        xhr=True
    )

    # Risk views

    config.add_route(
        'risks',
        '/risk_catalog/{id}/risks',
        factory=risk_catalog_factory
    )
    config.add_view(
        risks_view,
        route_name='risks',
        renderer='templates/table.pt',
    )

    config.add_route(
        'add_risk',
        '/risks_catalog/{id}/add',
        factory=risk_catalog_factory
    )
    config.add_view(
        edit_risk_view,
        route_name='add_risk',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_risk_view,
        route_name='add_risk',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'edit_risk',
        '/risks/{id}/edit',
        factory=risk_factory
    )
    config.add_view(
        edit_risk_view,
        route_name='edit_risk',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_risk_view,
        route_name='edit_risk',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'delete_risk',
        '/risks/{id}/delete',
        factory=risk_factory
    )
    config.add_view(
        delete_risk_view,
        route_name='delete_risk',
        xhr=False
    )
    config.add_view(
        delete_risk_view,
        route_name='delete_risk',
        renderer='json',
        request_method='DELETE',
        xhr=True
    )

    # Risk assessment views

    config.add_route(
        'assessment',
        '/assessment',
        factory=organization_factory
    )
    config.add_view(
        assessment_view,
        route_name='assessment',
        renderer='templates/table.pt',
    )

    config.add_route(
        'assess_impact',
        '/assessment/impact',
        factory=organization_factory
    )
    config.add_view(
        assess_impact_view,
        route_name='assess_impact',
        renderer='templates/table.pt',
    )

    config.add_route(
        'assess_likelihood',
        '/assessment/likelihood',
        factory=organization_factory
    )
    config.add_view(
        assess_likelihood_view,
        route_name='assess_likelihood',
        renderer='templates/table.pt',
    )

    config.add_route(
        'generate_risk_matrix',
        '/assessment/risk_matrix',
        factory=organization_factory
    )
    config.add_view(
        generate_risk_matrix_view,
        route_name='generate_risk_matrix',
        renderer='templates/matrix.pt',
    )

    config.add_route(
        'edit_assessment',
        '/assessments/{id}/edit',
        factory=risk_factory
    )
    config.add_view(
        edit_assessment_view,
        route_name='edit_assessment',
        renderer='templates/form.pt',
        xhr=False
    )
    config.add_view(
        edit_assessment_view,
        route_name='edit_assessment',
        renderer='json',
        request_method='POST',
        xhr=True
    )

    config.add_route(
        'set_impact',
        '/assessments/{id}/impact/{level}',
        factory=risk_assessment_factory
    )
    config.add_view(
        set_impact_view,
        route_name='set_impact',
        renderer='json',
        request_method='PUT',
        xhr=True
    )

    config.add_route(
        'set_likelihood',
        '/assessments/{id}/likelihood/{level}',
        factory=risk_assessment_factory
    )
    config.add_view(
        set_likelihood_view,
        route_name='set_likelihood',
        renderer='json',
        request_method='PUT',
        xhr=True
    )
