from pyramid.authorization import Allow

from riskmatrix.models import Organization


def test_acl(config):
    session = config.dbsession
    org = Organization(name='Test', email='test@example.com')
    session.add(org)
    session.flush()

    assert org.__acl__() == [
        (Allow, f'org_{org.id}', ['view']),
    ]
