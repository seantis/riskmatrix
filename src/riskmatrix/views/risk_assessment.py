from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
from sqlalchemy.orm import contains_eager
from uuid import uuid4
from wtforms import StringField
from wtforms import TextAreaField

from riskmatrix.controls import Button
from riskmatrix.models import RiskAssessment
from riskmatrix.data_table import AJAXDataTable
from riskmatrix.data_table import DataColumn
from riskmatrix.data_table import maybe_escape
from riskmatrix.i18n import _
from riskmatrix.static import xhr_edit_js
from riskmatrix.views.asset import AssetTable
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
        <input class="form-check-input radio-button" type="radio"
            name="{name}" id="{name}-{value}" value="{value}"
            data-url="{url}" {checked}/>
        <label class="form-check-label" for="{name}-{value}">{value}</label>
    </div>
""")

# create radio template but hits the 


def render_impact_input(data: int | None, row) -> Markup:
    # FIXME: Maybe render_data should always have acces to the row.id
    return Markup('').join(
        _RADIO_TEMPLATE.format(
            name=row.id,
            value=value,
            checked='checked' if data == value else '',
            url=f'/assessments/{row.id}/impact/{value}'
        ) for value in range(1, 6)
    )

def render_likelihood_input(data: int | None, row) -> Markup:
    # FIXME: Maybe render_data should always have acces to the row.id
    return Markup('').join(
        _RADIO_TEMPLATE.format(
            name=row.id,
            value=value,
            checked='checked' if data == value else '',
            url=f'/assessments/{row.id}/likelihood/{value}'
        ) for value in range(1, 6)
    )


class AssessImpactTable(AssessmentBaseTable):
    asset_name = DataColumn(_('Asset'))
    impact = DataColumn(
        _('Impact'),
        format_data=render_impact_input,
        sort_key=lambda d: -1 if d is None else d
    )


class AssessLikelihoodTable(AssessmentBaseTable):
    asset_name = DataColumn(_('Asset'))
    likelihood = DataColumn(
        _('Likelihood'),
        format_data=render_likelihood_input,
        sort_key=lambda d: -1 if d is None else d
    )


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

import io
import matplotlib.pyplot as plt
from pyramid.response import Response
import base64
import numpy as np

def risk_matrix(
    context: RiskAssessment,
    request: 'IRequest'):


    table = AssessmentTable(context, request)
    # Fetch data from the database, 
    risks = table.query().all()

    # Create the plot
    # Create the plot
    fig = plt.figure(figsize=(10, 10))
    plt.subplots_adjust(wspace=0, hspace=0)

    nrows = 5
    ncols = 5
    axes = [fig.add_subplot(nrows, ncols, r * ncols + c + 1) for r in range(nrows) for c in range(ncols)]

    # Set limits and remove ticks for each subplot
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
    plt.xticks([])
    plt.yticks([])
    plt.xlim(0, 5)
    plt.ylim(0, 5)
    # Add labels to the axes
    for i in range(1, 6):
        # Add labels to the left side (Likelihood)
        axes[(5 - i) * ncols].set_yticks([2.5])
        axes[(5 - i) * ncols].set_yticklabels([str(i)])
        
        # Add labels to the bottom (Consequence)
        axes[ncols * (nrows - 1) + i - 1].set_xticks([2.5])
        axes[ncols * (nrows - 1) + i - 1].set_xticklabels([str(i)])

    plt.xlabel('Impact')
    plt.ylabel('Likelihood')

    nrows = 5
    ncols = 5
    axes = [fig.add_subplot(nrows, ncols, r * ncols + c + 1) for r in range(0, nrows) for c in range(0, ncols)]

    # remove the x and y ticks and set limits
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)

    # Define colors for each risk level
    green = [10, 15, 16, 20, 21]  # Green boxes
    yellow = [0, 5, 6, 11, 17, 22, 23]  # Yellow boxes
    orange = [1, 2, 7, 12, 13, 18, 19, 24]  # Orange boxes
    red = [3, 4, 8, 9, 14]  # Red boxes

    # Set background colors for each box
    for index in green:
        axes[index].set_facecolor('green')
    for index in yellow:
        axes[index].set_facecolor('yellow')
    for index in orange:
        axes[index].set_facecolor('orange')
    for index in red:
        axes[index].set_facecolor('red')

    # Plot the data from the database
    for risk in risks:
        # Adjust for 0-indexed plot coordinates (subtract 1)
        plot_x = risk.likelihood - 1
        plot_y = 4 - (risk.impact - 1)  # Invert the y-axis
        ax_index = plot_y * ncols + plot_x
        if 0 <= ax_index < len(axes):
            noise_x = np.random.uniform(-0.125, 0.125, (1 ))
            noise_y = np.random.uniform(-0.125, 0.125, (1))
            axes[ax_index].plot(plot_x + noise_x, plot_y+noise_y, 'ko', color='black')

    # Save the plot to a BytesIO object
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight')
    img_io.seek(0)
    img_data = img_io.getvalue()

    # Convert the image to Base64
    img_base64 = base64.b64encode(img_data).decode('utf-8')
    return {
        'title': _('Assess Likelihood'),
        'table': Markup(f"<img src='data:image/png;base64,{img_base64}' style='display: block; margin-left: auto; margin-right: auto;'/> "),
        'top_buttons': [],
    }

    # Serve the image
    return Response(body_file=img, content_type='image/png')