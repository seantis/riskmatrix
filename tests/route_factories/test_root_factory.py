from riskmatrix.models.root import Root
from riskmatrix.route_factories import root_factory
from riskmatrix.testing import DummyRequest


def test_root_factory(config):
    request = DummyRequest()
    assert isinstance(root_factory(request), Root)
