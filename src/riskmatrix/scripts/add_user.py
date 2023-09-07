import argparse
import sys

from getpass import getpass
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from pyramid.paster import setup_logging

from riskmatrix.models import Organization
from riskmatrix.models import User
from riskmatrix.orm import get_engine
from riskmatrix.orm import Base
from riskmatrix.scripts.util import select_existing_organization


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from typing import TypedDict

    class OrgDetails(TypedDict):
        name: str
        email: str

    class UserDetails(TypedDict):
        first_name: str
        last_name: str
        email: str

    class UserDetailsWithPassword(UserDetails):
        password: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])


def prompt_user_details() -> 'UserDetailsWithPassword':
    details: 'UserDetailsWithPassword' = {
        'first_name': input('First name: ').strip(),
        'last_name': input('Last name: ').strip(),
        'email': input('E-Mail: ').strip(),
        'password': ''
    }
    passwords_match = False
    while not passwords_match:
        password = getpass('Password: ')
        passwords_match = password == getpass('Confirm Password: ')
        if passwords_match:
            details['password'] = password
        else:
            print("Passwords didn't match!")

    return details


def prompt_organization_details() -> 'OrgDetails':
    return {
        'name': input('Organization name: ').strip(),
        'email': input('Organization sender e-mail: ').strip()
    }


def print_details(
    user_details: 'UserDetailsWithPassword',
    existing_org: Organization | None,
    org_details:  'OrgDetails | None'
) -> None:

    print('First name: ' + user_details['first_name'])
    print('Last name:  ' + user_details['last_name'])
    print('E-Mail:     ' + user_details['email'])
    print('Password:   ' + '*'*len(user_details['password']))
    if existing_org:
        print('Add to existing organization.')
        print('Name:       ' + existing_org.name)
    else:
        assert org_details
        print('Create and add to new organization.')
        print('Name:       ' + org_details['name'])
        print('E-Mail:     ' + org_details['email'])
    print('')


def add_user(db: 'Session') -> None:
    user_details = prompt_user_details()
    print('Create and add to new organization? [Y/n]')
    existing_org = None
    org_details = None
    if input('').strip().lower() == 'n':
        existing_org = select_existing_organization(db)
    if existing_org is None:
        print('Creating new organization')
        org_details = prompt_organization_details()

    print('')
    print('Creating user with the following details:')
    print_details(user_details, existing_org, org_details)
    print('Does this look correct? [Y/n]')
    if input('').strip().lower() == 'n':
        print('Aborting')
        exit()

    if existing_org:
        org = existing_org
    else:
        assert org_details
        org = Organization(**org_details)
        db.add(org)
        db.flush()
        db.refresh(org)

    user = User(**user_details, organization=org)
    db.add(user)
    db.flush()
    print('Successfully created new user.')


def main(argv: list[str] = sys.argv) -> None:
    args = parse_args(argv)
    setup_logging(args.config_uri)
    with bootstrap(args.config_uri) as env:
        settings = get_appsettings(args.config_uri)

        engine = get_engine(settings)
        Base.metadata.create_all(engine)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            add_user(dbsession)
