import riskmatrix.models


def test_includeme(config):
    config.include(riskmatrix.models)
