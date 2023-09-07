from riskmatrix.layouts import flash
from riskmatrix.testing import DummyRequest


def test_flash():
    request = DummyRequest()
    request.messages.add('Informational Message.')
    request.messages.add('Critical Error.', 'error')
    assert flash(None, request) == {
        'messages': [
            {'message': 'Informational Message.', 'type': 'info'},
            {'message': 'Critical Error.', 'type': 'danger'},
        ]
    }


def test_flash_no_messages():
    request = DummyRequest()
    assert flash(None, request) == {}
