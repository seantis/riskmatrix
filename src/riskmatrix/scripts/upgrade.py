import argparse
import os
import plaster
import transaction
from alembic.migration import MigrationContext
from alembic.operations import Operations
from enum import Enum
from sqlalchemy import inspect
from sqlalchemy.sql import text
from zope.sqlalchemy import mark_changed

from riskmatrix.orm import get_engine
from riskmatrix.orm import get_session_factory
from riskmatrix.orm import Base


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy import Column
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


class UpgradeContext:

    def __init__(self, db: 'Session'):
        self.session = db
        self.engine: 'Engine' = self.session.bind  # type:ignore

        self.operations_connection = db._connection_for_bind(
            self.engine
        )
        self.operations: Any = Operations(
            MigrationContext.configure(
                self.operations_connection
            )
        )

    def has_table(self, table: str) -> bool:
        inspector = inspect(self.operations_connection)
        return table in inspector.get_table_names()

    def drop_table(self, table: str) -> bool:
        if self.has_table(table):
            self.operations.drop_table(table)
            return True
        return False

    def has_column(self, table: str, column: str) -> bool:
        if not self.has_table(table):
            return False
        inspector = inspect(self.operations_connection)
        return column in {c['name'] for c in inspector.get_columns(table)}

    def add_column(self, table:  str, column: 'Column[Any]') -> bool:
        if self.engine.name != 'postgresql':
            return False

        if self.has_table(table):
            if not self.has_column(table, column.name):
                self.operations.add_column(table, column)
                return True
        return False

    def drop_column(self, table: str, name: str) -> bool:
        if self.engine.name != 'postgresql':
            return False

        if self.has_table(table):
            if self.has_column(table, name):
                self.operations.drop_column(table, name)
                return True
        return False

    def get_unique_constraint(
        self,
        table:         str,
        *column_names: str
    ) -> str | None:

        if self.engine.name != 'postgresql':
            return None

        inspector = inspect(self.operations_connection)
        for con in inspector.get_unique_constraints(table):
            if list(con['column_names']) == list(column_names):
                return con['name']
        return None

    def add_unique_constraint(self, table: str, *column_names: str) -> bool:
        if self.engine.name != 'postgresql':
            return False

        if self.has_table(table):
            name = self.get_unique_constraint(table, *column_names)
            if not name:
                # NOTE: This is not quite the same schema sqlalchemy
                #       uses for naming, but it's guaranteed to avoid
                #       collisions, so it should be fine...
                name = '_'.join(('uq', table) + column_names)
                self.operations.create_unique_constraint(
                    name,
                    table,
                    column_names
                )
                return True
        return False

    def drop_unique_constraint(self, table: str, *column_names: str) -> bool:
        if self.engine.name != 'postgresql':
            return False

        if self.has_table(table):
            name = self.get_unique_constraint(table, *column_names)
            if name:
                self.operations.drop_constraint(name, table, 'unique')
                return True
        return False

    def get_enum_values(self, enum_name: str) -> set[str]:
        if self.engine.name != 'postgresql':
            return set()

        # NOTE: This is very low-level but easier than using
        #       the sqlalchemy bind with a regular execute().
        result = self.operations_connection.execute(
            text("""
            SELECT pg_enum.enumlabel AS value
              FROM pg_enum
              JOIN pg_type
                ON pg_type.oid = pg_enum.enumtypid
             WHERE pg_type.typname = :enum_name
             GROUP BY pg_enum.enumlabel
            """),
            {'enum_name': enum_name}
        )
        return {value for (value,) in result}

    def update_enum_values(self, enum_type: type[Enum]) -> bool:
        # NOTE: This only adds new values, it doesn't remove
        #       old values. But the latter should probably
        #       not be a valid use case anyways.
        if self.engine.name != 'postgresql':
            return False

        assert issubclass(enum_type, Enum)
        # TODO: If we ever use a custom type name we need to
        #       be able to specify it. By default sqlalchemy
        #       uses the Enum type Name in lowercase.
        enum_name = enum_type.__name__.lower()
        existing = self.get_enum_values(enum_name)
        missing = {v.name for v in enum_type} - existing
        if not missing:
            return False

        # HACK: ALTER TYPE has to be run outside transaction
        self.operations.execute('COMMIT')
        for value in missing:
            # NOTE: This should be safe just by virtue of naming
            #       restrictions on classes and enum members
            self.operations.execute(
                f"ALTER TYPE {enum_name} ADD VALUE '{value}'"
            )
        # start a new transaction
        self.operations.execute('BEGIN')
        return True

    def commit(self) -> None:
        mark_changed(self.session)
        transaction.commit()


def upgrade(args: argparse.Namespace) -> None:

    # Extract settings from INI config file.
    # We cannot use pyramid.paster.bootstrap() because loading the application
    # requires the proper DB structure.
    defaults = {'here': os.getcwd()}
    settings = plaster.get_settings(
        args.config_uri,
        'app:main',
        defaults=defaults
    )

    # Setup DB.
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(engine)
    dbsession = session_factory()

    context = UpgradeContext(dbsession)
    module = __import__('riskmatrix', fromlist='*')
    func = getattr(module, 'upgrade', None)
    if func is not None:
        print('Upgrading riskmatrix')
        func(context)
    else:
        print('No pending upgrades')

    if not args.dry:
        context.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description='Runs all upgrade steps')
    parser.add_argument('config_uri', help='Config file')
    parser.add_argument('-d', '--dry', help='Dry run', action='store_true')
    args = parser.parse_args()

    if args.dry:
        print('Dry run')

    upgrade(args)

if __name__ == '__main__':
    main()
