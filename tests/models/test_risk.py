import pytest
from pyramid.authorization import Allow
from sqlalchemy.exc import IntegrityError

from riskmatrix.models import Organization
from riskmatrix.models import Risk
from riskmatrix.models import RiskCatalog
from riskmatrix.models import RiskCategory


def test_category_foreign_key(config, organization):
    session = config.dbsession
    organization2 = Organization('Test 2', 'test2@example.com')
    session.add(organization2)
    session.flush()

    catalog = RiskCatalog('Cloud Provider', organization)
    session.add(catalog)
    session.flush()

    category = RiskCategory('Operational', organization)
    category2 = RiskCategory('Financial', organization2)
    session.add_all([category, category2])
    session.flush()

    # we can add a category defined within our organization
    risk = Risk('Fire', catalog, category='Operational')
    session.add(risk)
    session.flush()
    assert risk.category == 'Operational'

    # and updates get cascaded
    category.name = 'Ops'
    session.flush()
    session.refresh(risk)
    assert risk.category == 'Ops'

    # but we're not allowed to refer to categories defined in
    # another organization
    risk2 = Risk('Investment loss', catalog, category='Financial')
    session.add(risk2)
    with pytest.raises(IntegrityError):
        session.flush()


def test_acl(config, organization):
    session = config.dbsession
    catalog = RiskCatalog('Cloud Provider', organization)
    session.add(catalog)
    session.flush()
    risk = Risk('Fire', catalog)
    session.add(risk)
    session.flush()

    assert risk.__acl__() == [
        (Allow, f'org_{organization.id}', ['view']),
    ]
