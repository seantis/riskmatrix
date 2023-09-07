from riskmatrix.flash import MessageQueue
from riskmatrix.testing import DummyRequest


def test_add(config):
    request = DummyRequest()
    messages = MessageQueue(request)
    messages.add('Test', 'info')
    assert messages.pop() == [{'type': 'info', 'message': 'Test'}]
    assert messages.pop() == []

    messages.add('Caution', 'warning')
    messages.add('Faulty', 'error')
    assert messages.pop() == [
        {'type': 'warning', 'message': 'Caution'},
        {'type': 'danger', 'message': 'Faulty'},
    ]


def test_clear(config):
    request = DummyRequest()
    messages = MessageQueue(request)
    messages.add('Test', 'info')
    messages.clear()
    assert messages.pop() == []
