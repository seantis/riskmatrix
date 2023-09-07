from datetime import datetime
from datetime import timedelta
from pyramid.authorization import ACLAllowed
from pyramid.authorization import ACLDenied
from pyramid.authorization import Allow
from pyramid.authorization import Authenticated
from pyramid.authorization import DENY_ALL
from pyramid.interfaces import ISecurityPolicy
from sqlalchemy.orm import object_session

from riskmatrix.models import User
from riskmatrix.security_policy import SessionSecurityPolicy
from riskmatrix.testing import DummyRequest
from riskmatrix.testing import verify_interface


def test_interface():
    verify_interface(SessionSecurityPolicy, ISecurityPolicy)


def test_acl(config):
    policy = SessionSecurityPolicy()
    context = object()
    request = DummyRequest()
    assert policy.acl(context, request) == [DENY_ALL]

    class ACLContext:
        def __acl__(self):
            return [(Allow, 'group:users', ['view'])]

    context = ACLContext()
    assert policy.acl(context, request) == [(Allow, 'group:users', ['view'])]


def test_principals(config, user):
    policy = SessionSecurityPolicy()
    request = DummyRequest()
    request.session['auth.userid'] = user.id
    assert policy.principals(request) == [
        Authenticated,
        f'user:{user.id}',
        f'org_{user.organization.id}',
    ]


def test_authenticated_userid():
    policy = SessionSecurityPolicy()
    request = DummyRequest()
    assert policy.authenticated_userid(request) is None

    request = DummyRequest()
    request.session['auth.userid'] = 'user:test'
    assert policy.authenticated_userid(request) == 'user:test'


def test_authenticated_userid_timeout():
    policy = SessionSecurityPolicy()
    request = DummyRequest()
    assert policy.authenticated_userid(request) is None

    request = DummyRequest()
    request.session['auth.userid'] = 'my_user'
    request.session['auth.timeout'] = 10
    assert policy.authenticated_userid(request) == 'my_user'

    request = DummyRequest()
    request.session['auth.userid'] = 'my_user'
    request.session['auth.timeout'] = 10
    request.session.last_accessed = datetime.now().timestamp()
    assert policy.authenticated_userid(request) == 'my_user'

    request = DummyRequest()
    request.session['auth.userid'] = 'my_user'
    request.session['auth.timeout'] = 10
    ts = (datetime.now() - timedelta(seconds=9)).timestamp()
    request.session.last_accessed = ts
    assert policy.authenticated_userid(request) == 'my_user'

    request = DummyRequest()
    request.session['auth.userid'] = 'my_user'
    request.session['auth.timeout'] = 10
    ts = (datetime.now() - timedelta(seconds=11)).timestamp()
    request.session.last_accessed = ts
    assert policy.authenticated_userid(request) is None
    assert 'auth.userid' not in request.session
    assert 'auth.timeout' not in request.session

    request = DummyRequest()
    request.session['auth.userid'] = 'my_user'
    request.session['auth.timeout'] = 10
    ts = (datetime.now() - timedelta(days=1)).timestamp()
    request.session.last_accessed = ts
    assert policy.authenticated_userid(request) is None


def test_forget():
    policy = SessionSecurityPolicy()
    request = DummyRequest()
    policy.remember(request, 'my_user')
    assert request.session['auth.userid'] == 'my_user'
    assert policy.forget(request) == []
    assert 'auth.userid' not in request.session
    assert 'auth.timeout' not in request.session

    policy = SessionSecurityPolicy(timeout=2700)
    request = DummyRequest()
    policy.remember(request, 'my_user')
    assert request.session['auth.userid'] == 'my_user'
    assert request.session['auth.timeout'] == 2700
    assert policy.forget(request) == []
    assert 'auth.userid' not in request.session
    assert 'auth.timeout' not in request.session


def test_identity(config, organization):
    session = config.dbsession
    policy = SessionSecurityPolicy()
    request = DummyRequest()
    assert policy.identity(request) is None

    user = User(organization=organization, email='test@example.com')
    session.add(user)
    session.flush()
    session.refresh(user)
    request = DummyRequest()
    request.session['auth.userid'] = user.id
    assert policy.identity(request).id == user.id
    assert request._authenticated_user.id == user.id
    # Cached on request
    assert policy.identity(request).id == user.id


def test_identity_detached(config, organization):
    session = config.dbsession
    policy = SessionSecurityPolicy()
    user = User(organization=organization, email='test@example.com')
    session.add(user)
    session.flush()
    session.refresh(user)
    request = DummyRequest()
    request.session['auth.userid'] = user.id
    assert policy.identity(request).id == user.id

    session.expunge(user)
    assert object_session(user) is None
    result = policy.identity(request)
    assert result.id == user.id
    assert object_session(result) is not None


def test_permits(config, organization):
    session = config.dbsession
    policy = SessionSecurityPolicy()

    user = User(organization=organization, email='test@example.com')
    session.add(user)
    session.flush()
    session.refresh(user)

    class ACLContext:
        def __acl__(self):
            return [(Allow, f'user:{user.id}', ['view'])]

    context = ACLContext()
    request = DummyRequest()
    result = policy.permits(request, context, 'view')
    assert isinstance(result, ACLDenied)
    result = policy.permits(request, context, 'edit')
    assert isinstance(result, ACLDenied)

    request = DummyRequest()
    request.session['auth.userid'] = user.id
    result = policy.permits(request, context, 'view')
    assert isinstance(result, ACLAllowed)
    result = policy.permits(request, context, 'edit')
    assert isinstance(result, ACLDenied)


def test_permits_no_acl_method(config):
    policy = SessionSecurityPolicy()

    context = object()
    request = DummyRequest()
    result = policy.permits(request, context, 'view')
    assert isinstance(result, ACLDenied)
    result = policy.permits(request, context, 'view')
    assert isinstance(result, ACLDenied)


def test_remember():
    policy = SessionSecurityPolicy()

    request = DummyRequest()
    assert policy.remember(request, 'my_user') == []
    assert request.session['auth.userid'] == 'my_user'
    assert 'auth.timeout' not in request.session

    policy = SessionSecurityPolicy(timeout=2700)
    request = DummyRequest()
    assert policy.remember(request, 'my_user') == []
    assert request.session['auth.userid'] == 'my_user'
    assert request.session['auth.timeout'] == 2700

    request = DummyRequest()
    assert policy.remember(request, 'my_user', max_age=100) == []
    assert request.session['auth.userid'] == 'my_user'
    assert request.session['auth.timeout'] == 100

    request = DummyRequest()
    assert policy.remember(request, 'my_user', max_age=None) == []
    assert request.session['auth.userid'] == 'my_user'
    assert 'auth.timeout' not in request.session
