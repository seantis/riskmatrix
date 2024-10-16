from fanstatic import Fanstatic
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from typing import Any
from email.headerregistry import Address
from pyramid.settings import asbool
from .mail import PostmarkMailer

from riskmatrix.flash import MessageQueue
from riskmatrix.i18n import LocaleNegotiator
from riskmatrix.layouts.steps import show_steps
from riskmatrix.route_factories import root_factory
from riskmatrix.security import authenticated_user
from riskmatrix.security_policy import SessionSecurityPolicy
from openai import OpenAI
from anthropic import Anthropic
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed.wsgi import WSGIApplication


__version__ = '0.0.0'


def includeme(config: Configurator) -> None:
    settings = config.registry.settings

    default_sender = settings.get(
        'email.default_sender',
        'riskmatrix@seantis.ch'
    )
    token = settings.get('mail.postmark_token', '')
    stream = settings.get('mail.postmark_stream', 'development')
    blackhole = asbool(settings.get('mail.postmark_blackhole', False))
    config.registry.registerUtility(PostmarkMailer(
        Address(addr_spec=default_sender),
        token,
        stream,
        blackhole=blackhole
    ))
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
    # wtforms 3.0 ships with its own translations
    config.add_translation_dirs('wtforms:locale')

    security_policy = SessionSecurityPolicy(timeout=28800)
    config.set_security_policy(security_policy)

    config.set_default_permission('view')
    config.set_default_csrf_options(require_csrf=True)

    config.add_request_method(authenticated_user, 'user', property=True)
    config.add_request_method(MessageQueue, 'messages', reify=True)
    config.add_request_method(show_steps, 'show_steps', reify=True)


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
            profiles_sample_rate=1.0,
            enable_tracing=True,
            send_default_pii=True
        )

    with Configurator(settings=settings, root_factory=root_factory) as config:
        includeme(config)

        if openai_apikey := settings.get('openai_api_key'):
            openai_client = ChatOpenAI(
                api_key=openai_apikey,
                model = "gpt-4o-mini",
                temperature=0.7
            )
            config.add_request_method(
                lambda r: openai_client,
                'llm',
                reify=True
            )
        elif anthropic_apikey := settings.get('anthropic_api_key'):
            anthropic_client = ChatAnthropic(
                api_key=anthropic_apikey,
                model="claude-3-5-sonnet-20240620",
                temperature=0.7
            )
            config.add_request_method(
                lambda r: anthropic_client,
                'llm',
                reify=True
            )
            
        if langfuse_host := settings.get("langfuse_host"):
            from langfuse.callback import CallbackHandler
            langfuse_handler = CallbackHandler(
                secret_key=settings.get("langfuse_secret_key"),
                public_key=settings.get("langfuse_public_key"),
                host=langfuse_host,
            )
            config.add_request_method(
                lambda r: langfuse_handler,
                'langfuse',
                reify=True
            )
 

    app = config.make_wsgi_app()
    return Fanstatic(app, versioning=True)
