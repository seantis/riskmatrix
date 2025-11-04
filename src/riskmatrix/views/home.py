from pyramid.httpexceptions import HTTPFound
from riskmatrix.i18n import _
from riskmatrix.views.table import Button

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..types import RenderData


def home_view(request: 'IRequest') -> 'RenderData':
    if request.authenticated_userid:
        # If user is authenticated, redirect to risk catalog
        return HTTPFound(location=request.route_url('risk_catalog'))
    
    # If user is not authenticated, redirect to login page
    return HTTPFound(location=request.route_url('login'))
