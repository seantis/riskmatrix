from dataclasses import dataclass
from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
from sqlalchemy.orm import contains_eager
from wtforms import StringField
from wtforms import TextAreaField
from wtforms.widgets import html_params

from riskmatrix.controls import Button
from riskmatrix.models import RiskAssessment
from riskmatrix.data_table import AJAXDataTable
from riskmatrix.data_table import DataColumn
from riskmatrix.data_table import maybe_escape
from riskmatrix.i18n import _
from riskmatrix.static import xhr_edit_js
from riskmatrix.wtform import Form
from riskmatrix.wtform.validators import Disabled


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm.query import Query
    from typing import TypeVar

    from riskmatrix.models import Organization
    from riskmatrix.types import MixedDataOrRedirect
    from riskmatrix.types import XHRData
    from riskmatrix.types import RenderData

    _Q = TypeVar('_Q', bound=Query[Any])


class AssessmentForm(Form):

    title = _('Edit Risk Assessment')

    def __init__(
        self,
        context: RiskAssessment | None,
        request: 'IRequest',
        prefix:  str = 'edit-xhr'
    ) -> None:

        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={
                'context': context,
                'dbsession': session
            }
        )

    name = StringField(
        label=_('Name'),
        validators=(
            Disabled(),
        )
    )

    description = TextAreaField(
        label=_('Description'),
        validators=(
            Disabled(),
        )
    )

    category = StringField(
        label=_('Category'),
        validators=(
            Disabled(),
        )
    )

    asset_name = StringField(
        label=_('Asset'),
        validators=(
            Disabled(),
        )
    )


def assessment_buttons(
    assessment: RiskAssessment,
    request: 'IRequest'
) -> list[Button]:

    return [Button(
        url=request.route_url('edit_assessment', id=assessment.id),
        icon='edit',
        description=_('Edit Risk'),
        css_class='btn-sm btn-secondary',
        modal='#edit-xhr',
    )]


class AssessmentBaseTable(AJAXDataTable[RiskAssessment]):
    default_options = {
        'length_menu': [[25, 50, 100, -1], [25, 50, 100, 'All']],
        'order': [[0, 'asc']]  # corresponds to column name
    }

    name = DataColumn(_('Name'))

    def apply_static_filters(self, query: '_Q') -> '_Q':
        query = query.join(RiskAssessment.risk)
        return query.filter(RiskAssessment.organization_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, '_total_records'):
            session = self.request.dbsession
            query = session.query(func.count(RiskAssessment.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def query(self) -> 'Query[RiskAssessment]':
        session = self.request.dbsession
        query = session.query(RiskAssessment)
        query = query.join(RiskAssessment.asset)
        query = self.apply_static_filters(query)
        query = query.options(
            contains_eager(RiskAssessment.asset),
            contains_eager(RiskAssessment.risk)
        )
        if self.order_by:
            column = getattr(RiskAssessment, self.order_by)
            query = query.order_by(getattr(column, self.order_dir)())
        else:
            query = query.order_by(RiskAssessment.name.asc())
        return query


class AssessmentTable(AssessmentBaseTable):
    description = DataColumn(_('Description'), class_name='visually-hidden')
    category = DataColumn(_('Category'))
    asset_name = DataColumn(_('Asset'))

    def __init__(self, org: 'Organization', request: 'IRequest') -> None:
        super().__init__(org, request, id='risks-table')
        xhr_edit_js.need()

    def buttons(
        self,
        assessment: RiskAssessment | None = None
    ) -> list[Button]:

        if assessment is None:
            return []

        return assessment_buttons(assessment, self.request)


_RADIO_TEMPLATE = Markup("""
    <div class="form-check form-check-inline">
        <input class="form-check-input" type="radio"
            name="{name}" id="{name}-{value}" value="{value}"
            data-url="{url}" data-csrf_token="{csrf_token}" {checked}/>
        <label class="form-check-label" for="{name}-{value}">{value}</label>
    </div>
""")


class AssessImpactTable(AssessmentBaseTable):
    asset_name = DataColumn(_('Asset'))
    impact = DataColumn(
        _('Impact'),
        sort_key=lambda d: -1 if d is None else d
    )

    def cell(self, column: DataColumn, row: RiskAssessment) -> str:
        if column.name == 'impact':
            cell_data = self._get(column.name)(row)
            params = {}
            if 'class_name' in column.options:
                params['class'] = column.options['class_name']
            if callable(column.sort_key):
                params['data_order'] = column.sort_key(cell_data)
            request = self.request
            data = Markup('').join(
                _RADIO_TEMPLATE.format(
                    name=row.id,
                    value=value,
                    url=request.route_url(
                        'set_impact', id=row.id, level=value,
                    ),
                    csrf_token=request.session.get_csrf_token(),
                    checked='checked' if row.impact == value else '',
                ) for value in range(1, 6)
            )
            return f'<td {html_params(**params)}>{data}</td>'
        else:
            return super().cell(column, row)


class AssessLikelihoodTable(AssessmentBaseTable):
    asset_name = DataColumn(_('Asset'))
    likelihood = DataColumn(
        _('Likelihood'),
        sort_key=lambda d: -1 if d is None else d
    )

    def cell(self, column: DataColumn, row: RiskAssessment) -> str:
        if column.name == 'likelihood':
            cell_data = self._get(column.name)(row)
            params = {}
            if 'class_name' in column.options:
                params['class'] = column.options['class_name']
            if callable(column.sort_key):
                params['data_order'] = column.sort_key(cell_data)
            request = self.request
            data = Markup('').join(
                _RADIO_TEMPLATE.format(
                    name=row.id,
                    value=value,
                    url=request.route_url(
                        'set_likelihood', id=row.id, level=value,
                    ),
                    csrf_token=request.session.get_csrf_token(),
                    checked='checked' if row.likelihood == value else '',
                ) for value in range(1, 6)
            )
            return f'<td {html_params(**params)}>{data}</td>'
        else:
            return super().cell(column, row)


def assessment_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderData':

    table = AssessmentTable(context, request)
    return {
        'title': _('Identify Risks'),
        'table': table,
        'top_buttons': [],
        'edit_form': AssessmentForm(None, request),
    }


def assess_impact_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderData':

    table = AssessImpactTable(context, request)
    return {
        'title': _('Assess Impact'),
        'table': table,
        'top_buttons': [],
    }


def assess_likelihood_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderData':

    table = AssessLikelihoodTable(context, request)
    return {
        'title': _('Assess Likelihood'),
        'table': table,
        'top_buttons': [],
    }


@dataclass
class Cell:
    value: str = ''
    css_class: str = ''
    title: str = ''
    header: bool = False
    colspan: int | None = None
    rowspan: int | None = None

    def __html__(self) -> str:
        tag = 'th' if self.header else 'td'
        params = ''
        if self.css_class:
            params += Markup(' class="{}"').format(self.css_class)
        if self.title:
            params += Markup(' title="{}"').format(self.title)
        if self.colspan:
            params += Markup(' colspan="{}"').format(self.colspan)
        if self.rowspan:
            params += Markup(' rowspan="{}"').format(self.rowspan)

        return Markup('<{tag} {params}>{value}</{tag}>').format(
            tag=tag,
            value=self.value,
            params=params,
        )


def generate_risk_matrix_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderData':

    cells = [
        [
            Cell(value='Impact', rowspan=6, css_class='rotate', header=True),
            Cell(value='5', title='Catastrophic', header=True),
            Cell(css_class='medium'),
            Cell(css_class='medium'),
            Cell(css_class='high'),
            Cell(css_class='high'),
            Cell(css_class='high'),
        ],
        [
            Cell(value='4', title='Major', header=True),
            Cell(css_class='low'),
            Cell(css_class='medium'),
            Cell(css_class='medium'),
            Cell(css_class='high'),
            Cell(css_class='high'),
        ],
        [
            Cell(value='3', title='Moderate', header=True),
            Cell(css_class='low'),
            Cell(css_class='medium'),
            Cell(css_class='medium'),
            Cell(css_class='medium'),
            Cell(css_class='high'),
        ],
        [
            Cell(value='2', title='Minor', header=True),
            Cell(css_class='low'),
            Cell(css_class='low'),
            Cell(css_class='medium'),
            Cell(css_class='medium'),
            Cell(css_class='medium'),
        ],
        [
            Cell(value='1', title='Insignificant', header=True),
            Cell(css_class='low'),
            Cell(css_class='low'),
            Cell(css_class='low'),
            Cell(css_class='low'),
            Cell(css_class='low'),
        ],
        [
            Cell(header=True),
            Cell(value='1', title='Rare', header=True),
            Cell(value='2', title='Unlikely', header=True),
            Cell(value='3', title='Possible', header=True),
            Cell(value='4', title='Likely', header=True),
            Cell(value='5', title='Almost Certain', header=True),
        ],
        [

            Cell(value='Likelihood', header=True, colspan=7),
        ]
    ]

    session = request.dbsession
    query = session.query(RiskAssessment)
    query = query.filter(RiskAssessment.organization_id == context.id)
    query = query.join(RiskAssessment.asset)
    query = query.join(RiskAssessment.risk)

    assessments = []
    for index, assessment in enumerate(query):
        impact = assessment.impact
        likelihood = assessment.likelihood
        if impact and likelihood:
            assessments.append({
                'nr': index + 1,
                'name': assessment.risk.name,
                'asset': assessment.asset.name,
                'impact': impact,
                'likelihood': likelihood,
            })

            severity = 'success'
            if impact * likelihood >= 5:
                severity = 'warning'
            if impact * likelihood >= 15:
                severity = 'danger'

            row = 5 - impact
            col = likelihood
            if row == 0:
                col += 1
            cells[row][col].value += Markup(
                ' <span class="badge rounded-pill bg-{severity} {css_class}"'
                ' title="{title}">{nr}</span>'
            ).format(
                severity=severity,
                nr=index + 1,
                title=f'{assessment.asset.name}: {assessment.risk.name}',
                css_class='text-dark' if severity == 'warning' else ''
            )

    return {
        'title': _('Risk Matrix'),
        'cells': cells,
        'assessments': assessments,
    }


def edit_assessment_view(
    context: RiskAssessment,
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    form = AssessmentForm(context, request)
    organization_id = context.risk.organization_id
    target_url = request.route_url('assessment', id=organization_id)
    if request.method == 'POST' and form.validate():
        form.populate_obj(context)
        if request.is_xhr:
            return {
                'name': maybe_escape(context.name),
                'description': maybe_escape(context.description),
                'category': maybe_escape(context.category),
            }
        else:
            return HTTPFound(location=target_url)
    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'target_url': target_url,
        }


def set_impact_view(
    context: RiskAssessment,
    request: 'IRequest'
) -> 'XHRData':

    raw_level = request.matchdict['level']
    try:
        level = int(raw_level)
    except (ValueError, TypeError):
        level = None

    if level not in range(1, 6):
        return {
            'error': _(
                'Invalid impact level "${level}" provided.',
                mapping={'level': raw_level}
            )
        }

    context.impact = level
    return {'success': ''}


def set_likelihood_view(
    context: RiskAssessment,
    request: 'IRequest'
) -> 'XHRData':

    raw_level = request.matchdict['level']
    try:
        level = int(raw_level)
    except (ValueError, TypeError):
        level = None

    if level not in range(1, 6):
        return {
            'error': _(
                'Invalid likelihood level "${level}" provided.',
                mapping={'level': raw_level}
            )
        }

    context.likelihood = level
    return {'success': ''}
