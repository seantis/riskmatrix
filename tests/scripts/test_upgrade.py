from sqlalchemy import Column, String

from riskmatrix.scripts.upgrade import UpgradeContext


def test_has_table(config):
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_table('user')
    assert not upgrade.has_table('bogus')


def test_drop_table(config):
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_table('user')
    assert upgrade.drop_table('user')
    assert not upgrade.has_table('user')
    assert not upgrade.drop_table('bogus')


def test_has_column(config):
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_column('user', 'id')
    assert not upgrade.has_column('user', 'bogus')
    assert not upgrade.has_column('bogus', 'id')


def test_add_column(config):
    # doesn't do anything on sqlite
    upgrade = UpgradeContext(config.dbsession)
    column = Column('new', String())
    assert not upgrade.has_column('user', 'new')
    assert not upgrade.add_column('user', column)
    assert not upgrade.has_column('user', 'new')


def test_pg_add_column(pg_config):
    upgrade = UpgradeContext(pg_config.dbsession)
    column = Column('new', String())
    assert not upgrade.has_column('user', 'new')
    assert upgrade.add_column('user', column)
    assert upgrade.has_column('user', 'new')
    assert not upgrade.add_column('user', column)


def test_drop_column(config):
    # doesn't do anything on sqlite
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_column('user', 'first_name')
    assert not upgrade.drop_column('user', 'first_name')
    assert upgrade.has_column('user', 'first_name')


def test_pg_drop_column(pg_config):
    upgrade = UpgradeContext(pg_config.dbsession)
    assert upgrade.has_column('user', 'first_name')
    assert upgrade.drop_column('user', 'first_name')
    assert not upgrade.has_column('user', 'first_name')
    assert not upgrade.drop_column('user', 'first_name')


def test_get_unique_constraint(config):
    # doesn't return anything on sqlite
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.get_unique_constraint(
        'user',
        'email',
    ) is None


def test_pg_get_unique_constraint(pg_config):
    # doesn't return anything on sqlite
    upgrade = UpgradeContext(pg_config.dbsession)
    assert upgrade.get_unique_constraint(
        'user',
        'email',
    ) == 'uq_user_email'


def test_add_unique_constraint(config):
    # doesn't do anything on sqlite
    upgrade = UpgradeContext(config.dbsession)
    assert not upgrade.add_unique_constraint('user', 'first_name')


def test_pg_add_unique_constraint(pg_config):
    upgrade = UpgradeContext(pg_config.dbsession)
    assert upgrade.get_unique_constraint('user', 'first_name') is None
    assert upgrade.add_unique_constraint('user', 'first_name')
    assert upgrade.get_unique_constraint('user', 'first_name') is not None
    assert not upgrade.add_unique_constraint('user', 'first_name')


def test_drop_unique_constraint(config):
    # doesn't do anything on sqlite
    upgrade = UpgradeContext(config.dbsession)
    assert not upgrade.drop_unique_constraint(
        'user',
        'email',
    )


def test_pg_drop_unique_constraint(pg_config):
    upgrade = UpgradeContext(pg_config.dbsession)
    assert upgrade.get_unique_constraint(
        'user',
        'email'
    ) is not None
    assert upgrade.drop_unique_constraint(
        'user',
        'email'
    )
    assert upgrade.get_unique_constraint(
        'user',
        'email'
    ) is None
    assert not upgrade.drop_unique_constraint(
        'user',
        'email'
    )


def test_commit(config):
    upgrade = UpgradeContext(config.dbsession)
    upgrade.drop_table('organization')
    upgrade.commit()
    # after commit the connection will be closed
