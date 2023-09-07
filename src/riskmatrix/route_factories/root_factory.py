from typing import TYPE_CHECKING

from riskmatrix.models.root import Root


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


def root_factory(request: 'IRequest') -> Root:
    return Root()
