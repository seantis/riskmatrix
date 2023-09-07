from riskmatrix.models import User


def test_init_password(config, organization):
    session = config.dbsession
    user = User(
        organization=organization,
        email='test@example.com',
        password='Test123!'
    )
    session.add(user)
    session.flush()
    assert user.email == 'test@example.com'
    assert user.password != 'Test123!'
    assert user.check_password('Test123!') is True


def test_set_password(config, organization):
    session = config.dbsession
    user = User(organization=organization, email='test@example.com')
    session.add(user)
    session.flush()
    user.set_password('Test123!')
    assert user.email == 'test@example.com'
    assert user.password != 'Test123!'
    assert user.check_password('Test123!') is True


def test_check_password(config, organization):
    session = config.dbsession
    user = User(organization=organization, email='test@example.com')
    session.add(user)
    session.flush()
    assert user.check_password('Test123!') is False
    user.set_password('Test123!')
    assert user.check_password(None) is False
    assert user.check_password('') is False
    assert user.check_password('Test123!') is True


def test_groups(config, organization):
    session = config.dbsession
    user = User(organization=organization, email='test@example.com')
    session.add(user)
    session.flush()
    assert user.groups() == [f'org_{organization.id}']
