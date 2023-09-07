import pytest

from pyramid.httpexceptions import HTTPForbidden

from riskmatrix.route_factories import organization_factory
from riskmatrix.testing import DummyRequest


def test_organization_factory_no_user(config):
    request = DummyRequest()
    with pytest.raises(HTTPForbidden):
        organization_factory(request)


def test_organization_factory(config, user):
    request = DummyRequest()
    org = organization_factory(request)
    assert org == user.organization
