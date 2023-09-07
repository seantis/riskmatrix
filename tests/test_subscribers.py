from pyramid.events import NewRequest
from pyramid.events import NewResponse

from riskmatrix.subscribers import csp_header
from riskmatrix.subscribers import sentry_context
from riskmatrix.testing import DummyRequest


def test_csp_header(config):
    request = DummyRequest()
    response = request.response
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == (
        "base-uri 'self'; "
        "child-src blob:; "
        "connect-src 'self' data:; "
        "default-src 'none'; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "object-src 'self'; "
        "script-src 'self' blob: resource:; "
        "style-src 'self' 'unsafe-inline'"
    )


def test_csp_header_sentry(config):
    config.registry.settings['sentry_dsn'] = 'https://aa:zz@sentry.io/22'
    request = DummyRequest()
    response = request.response
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == (
        "base-uri 'self'; "
        "child-src blob:; "
        "connect-src 'self' data: https://sentry.io; "
        "default-src 'none'; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "object-src 'self'; "
        "script-src 'self' blob: resource:; "
        "style-src 'self' 'unsafe-inline'; "
        "report-uri https://sentry.io/api/22/security/?sentry_key=aa"
    )

    config.registry.settings['sentry_dsn'] = 'https://aa@1.ingest.sentry.io/22'
    request = DummyRequest()
    response = request.response
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == (
        "base-uri 'self'; "
        "child-src blob:; "
        "connect-src 'self' data: https://1.ingest.sentry.io; "
        "default-src 'none'; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "object-src 'self'; "
        "script-src 'self' blob: resource:; "
        "style-src 'self' 'unsafe-inline'; "
        "report-uri https://sentry.io/api/22/security/?sentry_key=aa"
    )


def test_csp_header_existing(config):
    request = DummyRequest()
    response = request.response
    response.headers['Content-Security-Policy'] = "base-uri 'self';"
    event = NewResponse(request, response)
    csp_header(event)
    assert response.headers['Content-Security-Policy'] == "base-uri 'self';"


def test_sentry_context(config):
    request = DummyRequest()
    event = NewRequest(request)
    sentry_context(event)

    config.registry.settings['sentry_dsn'] = 'test'
    sentry_context(event)
