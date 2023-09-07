import logging
import os
import sys
from contextlib import contextmanager

from riskmatrix.models import Organization


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Iterator
    from sqlalchemy.orm import Session


@contextmanager
def lock_script(lock_dir: str, script_name: str) -> 'Iterator[str]':
    if not os.path.exists(lock_dir):
        os.makedirs(lock_dir, mode=0o755, exist_ok=True)

    lock_file = os.path.join(lock_dir, f'{script_name}.lock')
    if os.path.exists(lock_file):
        logger = logging.getLogger(script_name)
        logger.warning(
            'Lock file is still present. It will need to be removed manually '
            f'if there is no longer an active {script_name} process.'
        )
        sys.exit(0)

    with open(lock_file, mode='a'):
        pass  # creates lock file
    try:
        yield lock_file
    finally:
        os.remove(lock_file)


def select_existing_organization(db: 'Session') -> Organization | None:
    orgs = db.query(Organization).all()
    if not orgs:
        print('There are no existing organizations yet!')
        return None

    selected_org: Organization | None = None
    while selected_org is None:
        print('Select one of the following:')
        for index, org in enumerate(orgs):
            print(f'  [{index}]\t{org.name}')
        selected = input()
        try:
            selected_org = orgs[int(selected)]
        except (ValueError, IndexError):
            print(f'Invalid selection "{selected}"!')
    return selected_org
