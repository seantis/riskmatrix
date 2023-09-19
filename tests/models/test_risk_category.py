import pytest
from pyramid.authorization import Allow

from riskmatrix.models import Organization
from riskmatrix.models import RiskCategory


def test_hierarchy_foreign_key(config, organization):
    session = config.dbsession
    organization2 = Organization('Test 2', 'test2@example.com')
    session.add(organization2)
    session.flush()

    category = RiskCategory('Operational', organization)
    category2 = RiskCategory('Financial', organization2)
    session.add_all([category, category2])
    session.flush()

    # we can add a subcategory to a category defined within our organization
    subcategory = RiskCategory('Environment', organization, parent=category)
    session.add(subcategory)
    session.flush()
    assert subcategory.parent_id == category.id
    assert subcategory.parent == category
    assert category.children == [subcategory]

    # but we're not allowed to add them to categories defined in
    # another organization, ideally a ForeignKeyConstraint, much
    # like the one used on Risk would detect this case, but it
    # doesn't seem like it does (at least not in SQLite)
    with pytest.raises(ValueError, match=r'assigned to a different'):
        RiskCategory('Market', organization, parent=category2)

    # we're not allowed to modify the children directly
    # if we do it anyways, the change does not get flushed
    category.children.pop()
    session.flush()
    session.refresh(category)
    session.refresh(subcategory)
    assert category.children == [subcategory]
    assert subcategory.parent == category

    # if we delete a parent category all its children should be
    # deleted as well
    session.delete(category)
    session.flush()
    # session.get(RiskCategory, category.id) would be shorter, but
    # since it's backed by a cache it would not be an accurate check
    query = session.query(RiskCategory)
    assert query.filter(RiskCategory.id == category.id).first() is None
    assert query.filter(RiskCategory.id == subcategory.id).first() is None


def test_acl(config, organization):
    session = config.dbsession
    category = RiskCategory('Operational', organization)
    session.add(category)
    session.flush()

    assert category.__acl__() == [
        (Allow, f'org_{organization.id}', ['view']),
    ]
