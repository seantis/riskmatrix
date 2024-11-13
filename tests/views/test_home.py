from riskmatrix.testing import DummyRequest
from riskmatrix.views.home import home_view


def test_home_view(config):
    config.add_route('login', '/login')

    request = DummyRequest()
    response = home_view(request)
    assert response.status_int == 302
    expected_location = 'http://example.com/login'
    assert response.location == expected_location


def test_home_view_authenticated(config, user):
    config.add_route('risk_catalog', '/risk_catalog')

    request = DummyRequest()
    response = home_view(request)
    assert response.status_int == 302
    expected_location = 'http://example.com/risk_catalog'
    assert response.location == expected_location
