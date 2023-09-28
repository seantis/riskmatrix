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
                request.route_url('assessment')
            ),
            Step(
                _('Assess Impact'),
                request.route_url('assess_impact')
            ),
            Step(
                _('Assess Likelihood'),
                request.route_url('assess_likelihood')
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


def show_steps(request: 'IRequest') -> bool:
    # FIXME: For increased robustness we probably should store the
    #        steps in shared configuration and generate this condition
    #        from the defined steps
    route = request.matched_route
    if hasattr(route, 'name'):
        return route.name in (
            'assessment',
            'assess_impact',
            'assess_likelihood'
        )
    return False
