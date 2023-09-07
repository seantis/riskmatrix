from pyramid.httpexceptions import HTTPForbidden


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest

    from riskmatrix.models import Organization


def organization_factory(request: 'IRequest') -> 'Organization':
    if not request.user:
        raise HTTPForbidden()

    return request.user.organization
