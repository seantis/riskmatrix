from riskmatrix.i18n import _

from typing import NamedTuple
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest

    from riskmatrix.models import Organization
    from riskmatrix.types import RenderData


class Step(NamedTuple):
    title: str
    url: str
    disabled: bool = False


def steps(context: 'Organization', request: 'IRequest') -> 'RenderData':
    return {
        'steps': [
            Step(
                _('Identify Risks'),
                request.route_url('risks', id=context.id)
            ),
            Step(
                _('Assess Impact'),
                request.route_url('risks_impact', id=context.id)
            ),
            Step(
                _('Assess Likelihood'),
                request.route_url('risks_likelihood', id=context.id)
            ),
            Step(
                _('Generate Risk Matrix'),
                '#'
            ),
            Step(
                _('Plan Actions'),
                '#',
                disabled=True
            ),
        ]
    }
