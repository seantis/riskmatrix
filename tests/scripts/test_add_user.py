import io
import pytest

from riskmatrix.models import Organization
from riskmatrix.models import User
from riskmatrix.scripts.add_user import add_user
from riskmatrix.scripts.add_user import print_details
from riskmatrix.scripts.add_user import prompt_organization_details
from riskmatrix.scripts.add_user import prompt_user_details
from riskmatrix.scripts.add_user import select_existing_organization


@pytest.fixture
def mock_input(monkeypatch):
    mock_input = io.StringIO()
    monkeypatch.setattr('sys.stdin', mock_input)

    def mock_getpass(prompt):
        print(prompt, end='')
        return mock_input.readline().rstrip('\n')
    monkeypatch.setattr(
        'riskmatrix.scripts.add_user.getpass', mock_getpass
    )
    return mock_input


def test_prompt_user_details(mock_input, capsys):
    mock_input.write('John\n')
    mock_input.write('Doe\n')
    mock_input.write('john.doe@example.com\n')
    mock_input.write('very_secure\n')
    mock_input.write('oops_typo\n')
    mock_input.write('very_secure\n')
    mock_input.write('very_secure\n')
    mock_input.seek(0)

    details = prompt_user_details()
    assert details['first_name'] == 'John'
    assert details['last_name'] == 'Doe'
    assert details['email'] == 'john.doe@example.com'
    assert details['password'] == 'very_secure'

    prompts, _ = capsys.readouterr()
    assert prompts == (
        'First name: '
        'Last name: '
        'E-Mail: '
        'Password: '
        'Confirm Password: '
        'Passwords didn\'t match!\n'
        'Password: '
        'Confirm Password: '
    )


def test_prompt_organization_details(mock_input, capsys):
    mock_input.write('Seantis GmbH\n')
    mock_input.write('info@seantis.ch\n')
    mock_input.seek(0)

    details = prompt_organization_details()
    assert details['name'] == 'Seantis GmbH'
    assert details['email'] == 'info@seantis.ch'

    prompts, _ = capsys.readouterr()
    assert prompts == (
        'Organization name: '
        'Organization sender e-mail: '
    )


def test_select_existing_organization(mock_input, capsys, config):
    session = config.dbsession
    assert select_existing_organization(session) is None

    prompts, _ = capsys.readouterr()
    assert prompts == 'There are no existing organizations yet!\n'

    org1 = Organization(name='Seantis GmbH', email='info@seantis.ch')
    session.add(org1)
    org2 = Organization(name='Geistlich Pharma', email='info@geistlich.ch')
    session.add(org2)
    session.flush()

    mock_input.write('invalid\n1')
    mock_input.seek(0)
    selected = select_existing_organization(session)
    assert selected.id == str(org2.id)

    prompts, _ = capsys.readouterr()
    assert prompts == (
        'Select one of the following:\n'
        '  [0]\tSeantis GmbH\n'
        '  [1]\tGeistlich Pharma\n'
        'Invalid selection "invalid"!\n'
        'Select one of the following:\n'
        '  [0]\tSeantis GmbH\n'
        '  [1]\tGeistlich Pharma\n'
    )


def test_print_details_new_organization(capsys):
    print_details(
        {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'very_secure'
        },
        None,
        {'name': 'Seantis GmbH', 'email': 'info@seantis.ch'}
    )

    printed, _ = capsys.readouterr()
    assert printed == (
        'First name: John\n'
        'Last name:  Doe\n'
        'E-Mail:     john.doe@example.com\n'
        'Password:   ***********\n'
        'Create and add to new organization.\n'
        'Name:       Seantis GmbH\n'
        'E-Mail:     info@seantis.ch\n'
        '\n'
    )


def test_print_details_existing_organization(capsys):
    print_details(
        {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'very_secure'
        },
        Organization(name='Seantis GmbH', email='info@seantis.ch'),
        None
    )

    printed, _ = capsys.readouterr()
    assert printed == (
        'First name: John\n'
        'Last name:  Doe\n'
        'E-Mail:     john.doe@example.com\n'
        'Password:   ***********\n'
        'Add to existing organization.\n'
        'Name:       Seantis GmbH\n'
        '\n'
    )


def test_add_user(mock_input, capsys, config):
    mock_input.write('John\n')
    mock_input.write('Doe\n')
    mock_input.write('john.doe@example.com\n')
    mock_input.write('very_secure\n')
    mock_input.write('very_secure\n')
    mock_input.write('\n')
    mock_input.write('Seantis GmbH\n')
    mock_input.write('info@seantis.ch\n')
    mock_input.write('\n')
    mock_input.seek(0)

    session = config.dbsession
    add_user(session)
    orgs = session.query(Organization).all()
    assert len(orgs) == 1
    assert orgs[0].name == 'Seantis GmbH'
    assert orgs[0].email == 'info@seantis.ch'

    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].first_name == 'John'
    assert users[0].last_name == 'Doe'
    assert users[0].email == 'john.doe@example.com'
    assert users[0].check_password('very_secure')
    assert users[0].organization == orgs[0]


def test_add_user_existing(mock_input, capsys, config):
    mock_input.write('John\n')
    mock_input.write('Doe\n')
    mock_input.write('john.doe@example.com\n')
    mock_input.write('very_secure\n')
    mock_input.write('very_secure\n')
    mock_input.write('n\n')
    mock_input.write('1\n')
    mock_input.write('y\n')
    mock_input.seek(0)

    session = config.dbsession
    org1 = Organization(name='Seantis GmbH', email='info@seantis.ch')
    session.add(org1)
    org2 = Organization(name='Geistlich Pharma', email='info@geistlich.ch')
    session.add(org2)

    session.flush()
    add_user(session)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].first_name == 'John'
    assert users[0].last_name == 'Doe'
    assert users[0].email == 'john.doe@example.com'
    assert users[0].check_password('very_secure')
    assert users[0].organization.id == str(org2.id)


def test_add_user_abort(mock_input, capsys, config):
    mock_input.write('John\n')
    mock_input.write('Doe\n')
    mock_input.write('john.doe@example.com\n')
    mock_input.write('very_secure\n')
    mock_input.write('very_secure\n')
    mock_input.write('\n')
    mock_input.write('Seantis GmbH\n')
    mock_input.write('info@seantis.ch\n')
    mock_input.write('N\n')
    mock_input.seek(0)

    session = config.dbsession
    with pytest.raises(SystemExit):
        add_user(session)
    assert session.query(Organization).all() == []
    assert session.query(User).all() == []
