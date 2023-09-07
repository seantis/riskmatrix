from fanstatic import Fanstatic
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from typing import Any

from riskmatrix.flash import MessageQueue
from riskmatrix.i18n import LocaleNegotiator
from riskmatrix.route_factories import root_factory
from riskmatrix.security import authenticated_user
from riskmatrix.security_policy import SessionSecurityPolicy


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed.wsgi import WSGIApplication


__version__ = '0.0.0'


def includeme(config: Configurator) -> None:
    settings = config.registry.settings

    config.include('pyramid_beaker')
    config.include('pyramid_chameleon')
    config.include('pyramid_layout')
    config.include('riskmatrix.models')
    config.include('riskmatrix.layouts')
    config.include('riskmatrix.views')
    config.include('riskmatrix.subscribers')

    session_factory = session_factory_from_settings(settings)
    config.set_session_factory(session_factory)

    config.set_locale_negotiator(LocaleNegotiator())
    config.add_translation_dirs('riskmatrix:locale')
    config.add_translation_dirs('wtforms:locale')

    security_policy = SessionSecurityPolicy(timeout=28800)
    config.set_security_policy(security_policy)

    config.set_default_permission('view')
    config.set_default_csrf_options(require_csrf=True)

    config.add_request_method(authenticated_user, 'user', property=True)
    config.add_request_method(MessageQueue, 'messages', reify=True)


def main(
    global_config: Any,
    **settings: Any
) -> 'WSGIApplication':  # pragma: no cover

    sentry_dsn = settings.get('sentry_dsn')
    sentry_environment = settings.get('sentry_environment', 'development')
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.pyramid import PyramidIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=sentry_environment,
            integrations=[PyramidIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=1.0,
            profiles_sample_rate=0.25,
        )

    with Configurator(settings=settings, root_factory=root_factory) as config:
        includeme(config)

    app = config.make_wsgi_app()
    return Fanstatic(app, versioning=True)
