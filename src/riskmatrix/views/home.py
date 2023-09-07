from pyramid.httpexceptions import HTTPFound


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def home_view(request: 'IRequest') -> HTTPFound:
    if request.authenticated_userid:
        # TODO: This should probably change
        url = request.route_url('organization')
    else:
        url = request.route_url('login')
    return HTTPFound(location=url)
