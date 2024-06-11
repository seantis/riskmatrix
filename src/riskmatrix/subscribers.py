from pyramid.events import NewRequest
from pyramid.events import NewResponse
import secrets

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.config import Configurator
    from pyramid.interfaces import IRequest


def default_csp_directives(request: 'IRequest') -> dict[str, str]:
    directives = {
        "base-uri": "'self'",
        "child-src": "blob:",
        "connect-src": "'self' data:",
        "default-src": "'none'",
        "font-src": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
        "img-src":  "'self' data: blob:",
        "object-src": "'self'",
        "script-src": f"'self' 'nonce-{request.csp_nonce}' blob: resource:",
        "style-src": "'self' 'unsafe-inline'",
    }

    sentry_dsn = request.registry.settings.get('sentry_dsn')
    if sentry_dsn:
        key = sentry_dsn.split('@')[0].split('/')[-1].split(':')[0]
        host = sentry_dsn.split('@')[1].split('/')[0]
        project = sentry_dsn.split('/')[-1]
        url = f'https://sentry.io/api/{project}/security/?sentry_key={key}'
        directives['report-uri'] = url
        directives['connect-src'] += f' https://{host}'
    return directives


def csp_header(event: NewResponse) -> None:
    response = event.response
    if 'Content-Security-Policy' not in response.headers:
        directives = default_csp_directives(event.request)
        csp = '; '.join([f'{k} {v}' for k, v in directives.items()])
        response.headers['Content-Security-Policy'] = csp


def sentry_context(event: NewRequest) -> None:
    sentry_dsn = event.request.registry.settings.get('sentry_dsn')
    request = event.request
    if sentry_dsn and request.user:
        from sentry_sdk import configure_scope
        with configure_scope() as scope:
            scope.user = {'id': request.user.id}

def request_none_generator(event: 'NewRequest') -> None:
    request = event.request
    request.set_property(lambda r: secrets.token_urlsafe(), 'csp_nonce', reify=True)


def includeme(config: 'Configurator') -> None:
    config.add_subscriber(csp_header, NewResponse)
    config.add_subscriber(request_none_generator, NewRequest)
    config.add_subscriber(sentry_context, NewRequest)
