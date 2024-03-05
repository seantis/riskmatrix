from dataclasses import dataclass
from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
from sqlalchemy.orm import contains_eager
from wtforms import StringField
from wtforms import TextAreaField
from wtforms.widgets import html_params
import plotly.graph_objects as go
import numpy as np

from riskmatrix.controls import Button
from riskmatrix.models import RiskAssessment, RiskMatrixAssessment
from riskmatrix.data_table import AJAXDataTable
from riskmatrix.data_table import DataColumn
from riskmatrix.data_table import maybe_escape
from riskmatrix.i18n import _
from riskmatrix.static import xhr_edit_js
from riskmatrix.wtform import Form
from riskmatrix.wtform.validators import Disabled


from typing import Any, Generator, TYPE_CHECKING
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


class AssessmentOverviewTable(AssessmentBaseTable):
    nr = DataColumn(_("Nr."))
    name = DataColumn(_("Name"))
    description = DataColumn(_("Description"), class_name="visually-hidden")
    category = DataColumn(_("Category"))
    asset_name = DataColumn(_("Asset"))
    likelihood = DataColumn(_("Likelihood"))
    impact = DataColumn(_("Impact"))

    def __init__(self, org: "Organization", request: "IRequest") -> None:
        super().__init__(org, request, id="risks-table")
        xhr_edit_js.need()

    def query(self) -> "Generator[RiskMatrixAssessment]":
        query = super().query()

        for idx, item in enumerate(query):
            item.nr = idx + 1
            yield item


_RADIO_TEMPLATE = Markup(
    """
    <div class="form-check form-check-inline">
        <input class="form-check-input" type="radio"
            name="{name}" id="{name}-{value}" value="{value}"
            data-url="{url}" data-csrf_token="{csrf_token}" {checked}/>
        <label class="form-check-label" for="{name}-{value}">{value}</label>
    </div>
"""
)


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


def plot_risk_matrix(risks: 'Query[RiskMatrixAssessment]') -> str:
    fig = go.Figure()

    # Define the colors for different risk levels
    colors = {
        "green": [10, 15, 16, 20, 21],
        "yellow": [0, 5, 6, 11, 17, 22, 23],
        "orange": [1, 2, 7, 12, 13, 18, 19, 24],
        "red": [3, 4, 8, 9, 14],
    }

    # Create a 5x5 grid and set the color for each cell
    for color, indices in colors.items():
        for index in indices:
            i, j = divmod(index, 5)

            fig.add_shape(
                type="rect",
                x0=j,
                y0=4 - i,
                x1=j + 1,
                y1=5 - i,
                line={"color": "white", "width": 0},
                fillcolor=color,
                layer="below",
            )

    # Plot points
    for risk in list(risks):
        if risk.likelihood and risk.impact:
            x, y = float(risk.likelihood - 1), float(4 - (risk.impact - 1))

            # Adjust the position within the cell to avoid overlap
            noise_x = np.random.uniform(0.1, 0.9)
            noise_y = np.random.uniform(0.1, 0.9)
            x, y = x + noise_x, y + noise_y

            fig.add_trace(
                go.Scatter(
                    x=[x],
                    y=[y],
                    text=[str(risk.nr)],
                    name="",
                    mode="markers+text",
                    marker={"color": "black", "size": 18},
                    textposition="middle center",
                    hoverinfo="text",
                    hovertemplate=f"{risk.nr} {risk.name} \
                    (Impact: {risk.impact} Likelihood: {risk.likelihood})",
                    textfont={"color": "white"},
                )
            )

    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    # Update layout
    fig.update_layout(
        xaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
            "range": [-0.5, 5]
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
            "range": [-0.5, 5]
        },
        showlegend=False,
        width=700,
        height=700,
        margin={"l": 5, "r": 5, "t": 5, "b": 5},  # Adjusted margins
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    # Add axis labels
    fig.add_annotation(
        x=2.5, y=-0.2, text="Impact", showarrow=False, font={"size": 20}
    )
    fig.add_annotation(
        x=-0.2,
        y=2.5,
        text="Likelihood",
        showarrow=False,
        textangle=-90,
        font={"size": 20},
    )

    return fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={
            "modeBarButtonsToRemove": ["zoom", "pan", "select", "lasso2d"]
        },
    )


def generate_risk_matrix_view(
    context: "Organization", request: "IRequest"
) -> "RenderData":
    table = AssessmentOverviewTable(context, request)

    return {
        "title": _("Risk Matrix"),
        "plot": Markup(plot_risk_matrix(table.query()).replace('<script', f'<script nonce="{request.csp_nonce}"')),  # noqa: MS001
        "table": table,
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
