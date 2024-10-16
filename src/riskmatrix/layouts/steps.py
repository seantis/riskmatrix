from markupsafe import Markup
from riskmatrix.i18n import _

from typing import NamedTuple
from typing import TYPE_CHECKING

from riskmatrix.models.risk_assessment import RiskAssessment
from riskmatrix.models.risk_assessment_info import RiskAssessmentInfo, RiskAssessmentState
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest

    from riskmatrix.models import Organization
    from riskmatrix.types import RenderData


class Step(NamedTuple):
    title: str
    url: str
    disabled: bool = False


def steps(context: 'Organization', request: 'IRequest') -> 'RenderData':
    assessments = request.dbsession.query(RiskAssessmentInfo).filter(
        RiskAssessmentInfo.organization_id == context.id,
        RiskAssessmentInfo.state == RiskAssessmentState.OPEN,
    ).all()

    t = request.dbsession.query(RiskAssessment).filter(RiskAssessment.risk_assessment_info_id.in_([a.id for a in assessments]), RiskAssessment.likelihood == None, RiskAssessment.impact == None).count()
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
                request.route_url('generate_risk_matrix')
            ),
            Step(
                Markup('<s>Plan Actions</s>'),
                '#',
                disabled=True
            ),
            Step(_("Finish Assessment"), request.route_url('finish_assessment'), disabled=False),#t > 0 or len(assessments) == 0),
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
            'assess_likelihood',
            'generate_risk_matrix',
            'finish_assessment'
        )
    return False
