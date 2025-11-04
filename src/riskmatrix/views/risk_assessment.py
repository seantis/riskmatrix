import json
import pytz
from markupsafe import Markup
from sedate import standardize_date
from pyramid.httpexceptions import HTTPFound
from riskmatrix.models.risk_assessment_info import (
    RiskAssessmentInfo,
    RiskAssessmentState,
)
from riskmatrix.models.risk_assessment_treatment import TreatmentType
from sqlalchemy import func
from sqlalchemy.orm import contains_eager
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import DateTimeLocalField
from wtforms.widgets import html_params
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from riskmatrix.controls import Button
from riskmatrix.models import RiskAssessment, RiskMatrixAssessment
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
    from sqlalchemy.orm import Session
    from typing import TypeVar

    from riskmatrix.models import Organization
    from riskmatrix.types import MixedDataOrRedirect
    from riskmatrix.types import XHRData
    from riskmatrix.types import RenderData

    _Q = TypeVar("_Q", bound=Query[Any])


def ensure_open_assessment_exists(
    organization: "Organization",
    session: "Session"
) -> RiskAssessmentInfo:
    """Ensure an open assessment exists for the organization.
    
    If no open assessment exists, create one with all asset/risk combinations.
    Returns the open assessment.
    """
    # Check if there's an open assessment
    open_assessment = (
        session.query(RiskAssessmentInfo)
        .filter(
            RiskAssessmentInfo.organization_id == organization.id,
            RiskAssessmentInfo.state != RiskAssessmentState.FINISHED
        )
        .first()
    )
    
    # If no open assessment exists, create one with all asset/risk combinations
    if not open_assessment:
        from riskmatrix.models import Asset, Risk
        from sedate import utcnow
        
        # Create new assessment info
        open_assessment = RiskAssessmentInfo(
            organization_id=organization.id,
            #name=f"Assessment {utcnow().strftime('%Y-%m-%d %H:%M')}",
            #state=RiskAssessmentState.OPEN
        )
        session.add(open_assessment)
        session.flush()  # Get the ID
        
        # Get all assets and risks for the organization
        assets = session.query(Asset).filter(Asset.organization_id == organization.id).all()
        risks = session.query(Risk).filter(Risk.organization_id == organization.id).all()
        
        # Create RiskAssessment entries for all combinations
        for asset in assets:
            for risk in risks:
                assessment = RiskAssessment(
                    asset=asset,
                    risk=risk,
                    info=open_assessment
                )
                session.add(assessment)
        
        session.flush()
    
    return open_assessment


class AssessmentForm(Form):
    title = _("Edit Risk Assessment")

    def __init__(
        self,
        context: RiskAssessment | None,
        request: "IRequest",
        prefix: str = "edit-xhr",
    ) -> None:
        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={"context": context, "dbsession": session},
        )

    name = StringField(label=_("Name"), validators=(Disabled(),))

    description = TextAreaField(
        label=_("Description"),
        validators=(Disabled(),)
    )

    category = StringField(label=_("Category"), validators=(Disabled(),))

    asset_name = StringField(label=_("Asset"), validators=(Disabled(),))


def assessment_buttons(
    assessment: RiskAssessment,
    request: "IRequest"
) -> list[Button]:
    return [
        Button(
            url=request.route_url("edit_assessment", id=assessment.id),
            icon="edit",
            description=_("Edit Risk"),
            css_class="btn-sm btn-secondary",
            modal="#edit-xhr",
        )
    ]


def compare_assessments_view(
    context: "Organization",
    request: "IRequest"
) -> "RenderData":
    table = AssessmentOverviewTable(context, request)

    base_query = AssessmentOverviewTable(context, request).query(
        append_numbers=False,
        ignore_risk_assessment_info_state=True
    )
    base_table = table.apply_filter_by_overview_id(
        base_query,
        request.matchdict.get("id_base")
    )
    table = AssessmentOverviewTable(context, request)

    compare_query = AssessmentOverviewTable(context, request).query(
        append_numbers=False,
        ignore_risk_assessment_info_state=True
    )
    comparison_table = table.apply_filter_by_overview_id(
        compare_query,
        request.matchdict.get("id_compare")
    )

    comarison_risks = list(comparison_table)
    base_risks = list(base_table)

    # use risk.risk_id + risk.asset_id as unique identifier
    total_risk_ids = set(
        [f"{risk.risk_id}-{risk.asset_id}" for risk in comarison_risks] +
        [f"{risk.risk_id}-{risk.asset_id}" for risk in base_risks]
    )

    risk_to_number_table = {risk: i+1 for i, risk in enumerate(total_risk_ids)}
    for risk in comarison_risks:
        risk.nr = risk_to_number_table[f"{risk.risk_id}-{risk.asset_id}"]
    for risk in base_risks:
        risk.nr = risk_to_number_table[f"{risk.risk_id}-{risk.asset_id}"]

    all_risks = comarison_risks + base_risks
    # deduplicate objects based on the id key
    all_risks = {
        f"{risk.risk_id}-{risk.asset_id}": risk
        for risk in all_risks
    }.values()
    # sort the risks by the number
    all_risks = sorted(all_risks, key=lambda risk: risk.nr)
    # set likelihood and impact to the one of base
    for risk in all_risks:
        risk_id_asset = f"{risk.risk_id}-{risk.asset_id}"
        risk_in_base = risk_id_asset in [
            f"{r.risk_id}-{r.asset_id}" for r in base_risks
        ]

        if not risk_in_base:
            risk.likelihood = next(
                (r.likelihood for r in comarison_risks if r == risk), None
            )
            risk.impact = next(
                (r.impact for r in comarison_risks if r == risk), None
            )
        else:
            risk.likelihood = next(
                (r.likelihood for r in base_risks if r == risk), None
            )
            risk.impact = next(
                (r.impact for r in base_risks if r == risk), None
            )

    # calculate the change if risk exists in both assessments
    for risk in all_risks:
        risk_id_asset = f"{risk.risk_id}-{risk.asset_id}"
        in_comparison = risk_id_asset in [
            f"{r.risk_id}-{r.asset_id}" for r in comarison_risks
        ]
        in_base = risk_id_asset in [
            f"{r.risk_id}-{r.asset_id}" for r in base_risks
        ]
        if in_comparison and in_base:
            risk_id_asset_str = f"{risk.risk_id}-{risk.asset_id}"
            comp_risk = next(
                (r for r in comarison_risks
                 if f"{r.risk_id}-{r.asset_id}" == risk_id_asset_str),
                None
            )

            if comp_risk.likelihood and risk.likelihood:
                risk.diff_likelihood = (risk.likelihood - comp_risk.likelihood)
            else:
                risk.diff_likelihood = None
            if comp_risk.impact and risk.impact:
                risk.diff_impact = (risk.impact - comp_risk.impact)
            else:
                risk.diff_impact = None
        else:
            risk.diff_likelihood = None
            risk.diff_impact = None

    comp_table = AssessmentComparisonTable(context, request, all_risks)

    # get the two assessment info objects
    base_assessment_info = (
        request.dbsession.query(RiskAssessmentInfo)
        .filter(RiskAssessmentInfo.id == request.matchdict.get("id_base"))
        .first()
    )
    comparison_assessment_info = (
        request.dbsession.query(RiskAssessmentInfo)
        .filter(RiskAssessmentInfo.id == request.matchdict.get("id_compare"))
        .first()
    )

    # Convert risks to the format expected by our template
    base_risks_data = []
    for risk in base_risks:
        if risk.likelihood and risk.impact:
            base_risks_data.append({
                'id': risk.nr if hasattr(risk, 'nr') else getattr(risk, 'id', None),
                'name': risk.name,
                'impact': risk.impact,
                'likelihood': risk.likelihood,
            })

    comparison_risks_data = []
    for risk in comarison_risks:
        if risk.likelihood and risk.impact:
            comparison_risks_data.append({
                'id': risk.nr if hasattr(risk, 'nr') else getattr(risk, 'id', None),
                'name': risk.name,
                'impact': risk.impact,
                'likelihood': risk.likelihood,
            })

    return {
        "title": _("Compare Risk Assessments"),
        "table": comp_table,
        "current_assessment": base_assessment_info,
        "comparison_assessment": comparison_assessment_info,
        "left_plot": render_risk_matrix(
            request, 
            base_risks_data, 
            'left', 
            _(""),
            font_size='small',
            likelihood_translation=_('Likelihood'),
            impact_translation=_('Impact'),
        ),
        "right_plot": render_risk_matrix(
            request, 
            comparison_risks_data, 
            'right', 
            _(""),
            font_size='small',
            likelihood_translation=_('Likelihood'),
            impact_translation=_('Impact'),
        )
    }


class AssessmentInfoTable(AJAXDataTable[RiskAssessmentInfo]):
    name = DataColumn(_("Name"))
    state = DataColumn(_("Status"))
    created = DataColumn(
        _("Erstellt"),
        format_data=lambda date: date.strftime("%d.%m.%Y %H:%M:%S")
    )
    finished_at = DataColumn(
        _("Geschlossen per"),
        format_data=lambda date: (
            date.strftime("%d.%m.%Y %H:%M:%S") if date else "-"
        )
    )

    def total_records(self) -> int:
        if not hasattr(self, "_total_records"):
            session = self.request.dbsession
            query = session.query(func.count(RiskAssessmentInfo.id))
            self._total_records: int = query.scalar()
        return self._total_records

    def query(self) -> "Query[RiskAssessment]":
        session = self.request.dbsession
        query = session.query(RiskAssessmentInfo)
        query = query.order_by(RiskAssessmentInfo.created.asc())
        return query

    def current_open_assessment(self) -> RiskAssessmentInfo | None:
        session = self.request.dbsession
        query = session.query(RiskAssessmentInfo).filter(
            RiskAssessmentInfo.organization_id == self.context.id,
            RiskAssessmentInfo.state != RiskAssessmentState.FINISHED
        )
        return query.first()

    def buttons(
        self,
        assessment: RiskAssessmentInfo | None = None
    ) -> list[Button]:
        if (assessment is None or
                assessment.state != RiskAssessmentState.FINISHED):
            return []

        # Check if there's an open assessment to compare with
        current_open = self.current_open_assessment()
        if current_open is None:
            return []

        return [
            Button(
                url=self.request.route_url(
                    "compare_assessments",
                    id_base=current_open.id,
                    id_compare=assessment.id
                ),
                icon="compress",
                description=_("Vergleich mit aktuellem Risk Assessment"),
                css_class="btn-sm btn",
            )
        ]


class AssessmentBaseTable(AJAXDataTable[RiskAssessment]):
    default_options = {
        "length_menu": [[-1], ["All"]],
        "order": [[0, "asc"]],  # corresponds to column name
    }

    name = DataColumn(_("Name"))

    def apply_static_filters(self, query: "_Q") -> "_Q":
        query = query.join(RiskAssessment.risk)
        return query.filter(RiskAssessment.organization_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, "_total_records"):
            session = self.request.dbsession
            query = session.query(func.count(RiskAssessment.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def query(
        self,
        ignore_risk_assessment_info_state=False
    ) -> "Query[RiskAssessment]":
        session = self.request.dbsession
        query = session.query(RiskAssessment)
        if not ignore_risk_assessment_info_state:
            query = query.join(RiskAssessment.risk_assessment_info)
            query = query.filter(
                RiskAssessmentInfo.state != RiskAssessmentState.FINISHED
            )
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
    description = DataColumn(_("Description"), class_name="visually-hidden")
    category = DataColumn(_("Category"))
    asset_name = DataColumn(_("Asset"))

    def __init__(self, org: "Organization", request: "IRequest") -> None:
        super().__init__(org, request, id="risks-table")
        xhr_edit_js.need()

    def buttons(
        self,
        assessment: RiskAssessment | None = None
    ) -> list[Button]:
        if assessment is None:
            return []

        return assessment_buttons(assessment, self.request)


class AssessmentComparisonTable(AssessmentBaseTable):
    nr = DataColumn(_("Nr."))
    name = DataColumn(_("Name"))
    description = DataColumn(_("Description"), class_name="visually-hidden")
    asset_name = DataColumn(_("Asset"))
    likelihood = DataColumn(_("Likelihood"))
    diff_likelihood = DataColumn(_("Change in Likelihood"))
    impact = DataColumn(_("Impact"))
    diff_impact = DataColumn(_("Change in Impact"))

    def __init__(self, org: "Organization", request: "IRequest", data) -> None:
        super().__init__(org, request, id="risks-table")
        xhr_edit_js.need()
        self.data = data

    def apply_filter_by_overview_id(self, query: "_Q", id) -> "_Q":
        query = query.join(RiskAssessment.risk_assessment_info)
        return query.filter(RiskAssessmentInfo.id == id)

    def query(
        self,
        append_numbers=True,
        ignore_risk_assessment_info_state=False
    ) -> "Query[RiskMatrixAssessment]":
        return self.data


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

    def apply_filter_by_overview_id(self, query: "_Q", id) -> "_Q":
        query = query.join(RiskAssessment.risk_assessment_info)
        return query.filter(RiskAssessmentInfo.id == id)

    def query(
        self,
        append_numbers=True,
        ignore_risk_assessment_info_state=False
    ) -> "Query[RiskMatrixAssessment]":
        query = super().query(
            ignore_risk_assessment_info_state=ignore_risk_assessment_info_state
        )
        if append_numbers:
            query = self.append_numbers(query)
        return query

    def append_numbers(self, query: "_Q") -> "_Q":
        numbered = []
        for i, entry in enumerate(query):
            entry.nr = i + 1
            numbered.append(entry)
        return numbered


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


class AssessmentFinishForm(Form):
    def __init__(
        self,
        context: RiskAssessment | None,
        request: "IRequest",
        prefix: str = "edit-xhr",
    ) -> None:
        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={"context": context, "dbsession": session},
        )

    display_name = StringField(label=_("Display Name"), validators=())
    end = DateTimeLocalField(
        label=_("Closed on"),
        validators=(),
        default=datetime.now()
    )


class AssessImpactTable(AssessmentBaseTable):
    asset_name = DataColumn(_("Asset"))
    impact = DataColumn(_("Impact"), sort_key=lambda d: -1 if d is None else d)

    def cell(self, column: DataColumn, row: RiskAssessment) -> str:
        if column.name == "impact":
            cell_data = self._get(column.name)(row)
            params = {}
            if "class_name" in column.options:
                params["class"] = column.options["class_name"]
            if callable(column.sort_key):
                params["data_order"] = column.sort_key(cell_data)
            request = self.request
            data = Markup("").join(
                    _RADIO_TEMPLATE.format(
                        name=row.id,
                        value=value,
                        url=request.route_url(
                            "set_impact",
                            id=row.id,
                            level=value,
                        ),
                        csrf_token=request.session.get_csrf_token(),
                        checked="checked" if row.impact == value else "",
                    )
                for value in range(1, 6)
                )
            return f"<td {html_params(**params)}>{data}</td>"
        else:
            return super().cell(column, row)


class AssessLikelihoodTable(AssessmentBaseTable):
    asset_name = DataColumn(_("Asset"))
    likelihood = DataColumn(
        _("Likelihood"),
        sort_key=lambda d: -1 if d is None else d
    )

    def cell(self, column: DataColumn, row: RiskAssessment) -> str:
        if column.name == "likelihood":
            cell_data = self._get(column.name)(row)
            params = {}
            if "class_name" in column.options:
                params["class"] = column.options["class_name"]
            if callable(column.sort_key):
                params["data_order"] = column.sort_key(cell_data)
            request = self.request
            data = Markup("").join(
                    _RADIO_TEMPLATE.format(
                        name=row.id,
                        value=value,
                        url=request.route_url(
                            "set_likelihood",
                            id=row.id,
                            level=value,
                        ),
                        csrf_token=request.session.get_csrf_token(),
                        checked="checked" if row.likelihood == value else "",
                    )
                for value in range(1, 6)
                )
            return f"<td {html_params(**params)}>{data}</td>"
        else:
            return super().cell(column, row)


def assessment_view(
    context: "Organization",
    request: "IRequest"
) -> "RenderData":
    # Ensure an open assessment exists
    ensure_open_assessment_exists(context, request.dbsession)
    
    table = AssessmentTable(context, request)
    return {
        "title": _("Identify Risks"),
        "table": table,
        "top_buttons": [],
        "edit_form": AssessmentForm(None, request),
    }


def assess_impact_view(
    context: "Organization",
    request: "IRequest"
) -> "RenderData":
    # Ensure an open assessment exists
    ensure_open_assessment_exists(context, request.dbsession)
    
    table = AssessImpactTable(context, request)
    return {
        "title": _("Assess Impact"),
        "table": table,
        "top_buttons": [],
    }


def assess_likelihood_view(
    context: "Organization", request: "IRequest"
) -> "RenderData":
    # Ensure an open assessment exists
    ensure_open_assessment_exists(context, request.dbsession)
    
    table = AssessLikelihoodTable(context, request)
    return {
        "title": _("Assess Likelihood"),
        "table": table,
        "top_buttons": [],
    }


class Cell:
    value: str = ""
    css_class: str = ""
    title: str = ""
    header: bool = False
    colspan: int | None = None
    rowspan: int | None = None

    def __html__(self) -> str:
        tag = "th" if self.header else "td"
        params = ""
        if self.css_class:
            params += Markup(' class="{}"').format(self.css_class)
        if self.title:
            params += Markup(' title="{}"').format(self.title)
        if self.colspan:
            params += Markup(' colspan="{}"').format(self.colspan)
        if self.rowspan:
            params += Markup(' rowspan="{}"').format(self.rowspan)

        return Markup("<{tag} {params}>{value}</{tag}>").format(
            tag=tag,
            value=self.value,
            params=params,
        )


def generate_risk_matrix_view(
    context: "Organization", request: "IRequest"
) -> "RenderData":
    # Ensure an open assessment exists
    ensure_open_assessment_exists(context, request.dbsession)
    
    table = AssessmentOverviewTable(context, request)
    risks = list(table.query())
    
    # Convert risks to the format expected by our template
    risks_data = []
    for risk in risks:
        if risk.likelihood and risk.impact:
            risks_data.append({
                'id': risk.nr if hasattr(risk, 'nr') else getattr(risk, 'id', None),
                'name': risk.name,
                'impact': risk.impact,
                'likelihood': risk.likelihood,
            })

    return {
        "title": _("Risk Matrix"),
        "plot": render_risk_matrix(request, risks_data, "single", font_size='big', likelihood_translation=_('Likelihood'), impact_translation=_('Impact')),
        "table": table,
    }


def generate_risk_matrix_compare_view(
    context: "Organization", request: "IRequest"
) -> "RenderData":
    table = AssessmentOverviewTable(context, request)
    risks = list(table.query())
    
    # Convert risks to the format expected by our template
    risks_data = []
    for risk in risks:
        if risk.likelihood and risk.impact:
            risks_data.append({
                'id': risk.nr if hasattr(risk, 'nr') else getattr(risk, 'id', None),
                'name': risk.name,
                'impact': risk.impact,
                'likelihood': risk.likelihood,
                'treated': {}
            })

    # Render the risk matrix using our template
    from pyramid.renderers import render
    plot = render(
        'templates/risk_matrix.pt',
        {
            'risks': json.dumps(risks_data),
            'treated': False,
            'request': request,
            'matrix_id': 'compare'
        },
        request=request
    )

    return {
        "title": _("Risk Matrix"),
        "plot": Markup(plot),
        "table": table,
    }


def plot_risk_matrix(risks: 'Query[RiskMatrixAssessment]', width: int = 600, height: int = 600) -> str:
    # Convert risks to a list of dictionaries for JSON serialization
    risks_data = []
    for risk in list(risks):
        if risk.likelihood and risk.impact:
            risk_data = {
                'id': risk.nr if hasattr(risk, 'nr') else getattr(risk, 'id', None),
                'name': risk.name,
                'impact': risk.impact,
                'likelihood': risk.likelihood,
                'treated': {}  # Empty treated object as per requirements
            }
            risks_data.append(risk_data)

    # Render the risk matrix template with the risks data
    from pyramid.renderers import render
    from pyramid.request import Request
    dummy_request = Request.blank('/')
    return render(
        'templates/risk_matrix.pt',
        {
            'risks': json.dumps(risks_data),
            'treated': False,
            'request': dummy_request,
            'matrix_id': 'plot'
        },
        request=dummy_request
    )


class PlotRisk:
    """Simple class to hold risk data for plotting."""
    def __init__(self, nr: int, name: str, likelihood: int | None, impact: int | None):
        self.nr = nr
        self.name = name
        self.likelihood = likelihood
        self.impact = impact


def render_risk_matrix(request, risks_data, matrix_id, title=None, font_size='small', likelihood_translation=None, impact_translation=None):
    """Helper function to render a risk matrix component."""
    from pyramid.renderers import render
    return Markup(render(
        'templates/components/risk_matrix.pt',
        {
            'risks': json.dumps(risks_data),
            'matrix_id': matrix_id,
            'request': request,
            'font_size': font_size,
            'likelihood_translation': likelihood_translation,
            'impact_translation': impact_translation
        },
        request=request
    ))


def finish_risk_assessment_view(
    context: "Organization",
    request: "IRequest"
) -> "MixedDataOrRedirect":
    if request.method == "GET":
        # Ensure an open assessment exists
        ensure_open_assessment_exists(context, request.dbsession)
        
        # Get all risk assessments for the current organization
        session = request.dbsession
        assessments = (
            session.query(RiskAssessment)
            .join(RiskAssessment.risk_assessment_info)
            .filter(
                RiskAssessment.organization_id == context.id,
                RiskAssessmentInfo.state != RiskAssessmentState.FINISHED
            )
            .all()
        )

        # Convert pre and post treatment risks to the format expected by our template
        pre_treatment_risks = []
        post_treatment_risks = []
        comparison_data = []
        
        for i, assessment in enumerate(assessments, 1):
            # Only add risks that have both likelihood and impact set
            if assessment.likelihood is not None and assessment.impact is not None:
                # Add risk to pre-treatment plot
                pre_treatment_risks.append({
                    'id': i,
                    'name': assessment.name,
                    'impact': assessment.impact,
                    'likelihood': assessment.likelihood,
                })
                
                # Add risk to post-treatment plot if it has valid post-treatment values
                post_impact = None
                post_likelihood = None
                
                if assessment.treatment:
                    if assessment.treatment.treatment_type == TreatmentType.REDUCE:
                        post_impact = assessment.treatment.post_impact
                        post_likelihood = assessment.treatment.post_likelihood
                    else:
                        post_impact = assessment.impact
                        post_likelihood = assessment.likelihood

                if post_impact is not None and post_likelihood is not None:
                    post_treatment_risks.append({
                        'id': i,
                        'name': assessment.name,
                        'impact': post_impact,
                        'likelihood': post_likelihood,
                    })

                # Add comparison data
                comparison_data.append({
                    'name': assessment.name,
                    'treatment_type': str(assessment.treatment.treatment_type) if assessment.treatment else 'Not Set',
                    'pre_likelihood': assessment.likelihood,
                    'post_likelihood': assessment.treatment.post_likelihood if assessment.treatment and assessment.treatment.treatment_type == TreatmentType.REDUCE else assessment.likelihood,
                    'pre_impact': assessment.impact,
                    'post_impact': assessment.treatment.post_impact if assessment.treatment and assessment.treatment.treatment_type == TreatmentType.REDUCE else assessment.impact
                })

        return {
            "title": _("Finish Risk Assessment"),
            "table": AssessmentInfoTable(context, request),
            "edit_form": AssessmentFinishForm(context, request),
            "pre_treatment_plot": render_risk_matrix(
                request, 
                pre_treatment_risks, 
                'pre', 
                _("Pre-Treatment Risk Matrix"),
                font_size='small',
                likelihood_translation=_('Likelihood'),
                impact_translation=_('Impact'),
            ),
            "post_treatment_plot": render_risk_matrix(
                request, 
                post_treatment_risks, 
                'post', 
                _("Post-Treatment Risk Matrix"),
                font_size='small',
                likelihood_translation=_('Likelihood'),
                impact_translation=_('Impact'),
            ),
            "comparison_data": comparison_data
        }

    assessment = request.dbsession.query(RiskAssessmentInfo).filter(
        RiskAssessmentInfo.organization_id == context.id,
        RiskAssessmentInfo.state != RiskAssessmentState.FINISHED
    ).all()

    existing_assessment_entries = (
        request.dbsession.query(RiskAssessment)
        .join(RiskAssessment.risk_assessment_info)
        .filter(
            RiskAssessment.organization_id == context.id,
            RiskAssessmentInfo.state != RiskAssessmentState.FINISHED
        )
        .all()
    )

    for entry in existing_assessment_entries:
        # Use only() to specify what we want to include rather than exclude
        # This is more explicit and avoids circular references
        rules = (
            "id", "impact", "likelihood", "meta", "created", "modified",
            "asset.id", "asset.name", "asset.description",
            "risk.id", "risk.name", "risk.description", "risk.category",
            "risk_assessment_info.id", "risk_assessment_info.name", "risk_assessment_info.state",
            "treatment.id", "treatment.description", "treatment.treatment_type", 
            "treatment.post_likelihood", "treatment.post_impact", "treatment.links"
        )
        entry.state_at_finish = json.dumps(entry.to_dict(only=rules))
        request.dbsession.add(entry)
        request.dbsession.flush()

    assessment_finish_form = AssessmentFinishForm(context, request)
    if not assessment_finish_form.validate():
        return {
            "form": assessment_finish_form,
            "errors": assessment_finish_form.errors,
        }

    for entry in assessment:
        entry.state = RiskAssessmentState.FINISHED
        # Convert naive datetime to timezone-aware UTC datetime
        finished_datetime = assessment_finish_form.end.data
        if finished_datetime:
            entry.finished_at = standardize_date(finished_datetime, timezone='UTC')
        entry.name = assessment_finish_form.display_name.data
        request.dbsession.add(entry)

    request.session.flash(_("Risk Assessment finished"), "success")
    return HTTPFound(location=request.route_url("assessment", id=context.id))


def edit_assessment_view(
    context: RiskAssessment, request: "IRequest"
) -> "MixedDataOrRedirect":
    form = AssessmentForm(context, request)
    organization_id = context.risk.organization_id
    target_url = request.route_url("assessment", id=organization_id)
    if request.method == "POST" and form.validate():
        form.populate_obj(context)
        if request.is_xhr:
            return {
                "name": maybe_escape(context.name),
                "description": maybe_escape(context.description),
                "category": maybe_escape(context.category),
            }
        else:
            return HTTPFound(location=target_url)
    if request.is_xhr:
        return {"errors": form.errors}
    else:
        return {
            "form": form,
            "target_url": target_url,
        }


def set_impact_view(context: RiskAssessment, request: "IRequest") -> "XHRData":
    raw_level = request.matchdict["level"]
    try:
        level = int(raw_level)
    except (ValueError, TypeError):
        level = None

    if level not in range(1, 6):
        return {
            "error": _(
                'Invalid impact level "${level}" provided.',
                mapping={"level": raw_level},
            )
        }

    context.impact = level
    return {"success": ""}


def set_likelihood_view(
    context: RiskAssessment,
    request: 'IRequest'
) -> 'XHRData':
    raw_level = request.matchdict["level"]
    try:
        level = int(raw_level)
    except (ValueError, TypeError):
        level = None

    if level not in range(1, 6):
        return {
            "error": _(
                'Invalid likelihood level "${level}" provided.',
                mapping={"level": raw_level},
            )
        }

    context.likelihood = level
    return {"success": ""}
