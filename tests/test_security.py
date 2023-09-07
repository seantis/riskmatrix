from riskmatrix.security import authenticated_user
from riskmatrix.security import query_user
from riskmatrix.testing import DummyRequest


def test_query_user(config, user):
    request = DummyRequest()
    assert query_user(None, None) is None
    assert query_user(None, request) is None
    assert query_user(user.id, None) is None
    assert query_user(user.id, request).id == user.id


def test_authenticated_user(config, user):
    request = DummyRequest()
    assert authenticated_user(request).id == user.id


def test_authenticated_user_not_authenticated(config):
    request = DummyRequest()
    assert authenticated_user(request) is None
