import json
import pytz
from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from riskmatrix.models.risk_assessment_info import (
    RiskAssessmentInfo,
    RiskAssessmentState,
)
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
    from typing import TypeVar

    from riskmatrix.models import Organization
    from riskmatrix.types import MixedDataOrRedirect
    from riskmatrix.types import XHRData
    from riskmatrix.types import RenderData

    _Q = TypeVar("_Q", bound=Query[Any])


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
    return {
        "title": _("Compare Risk Assessments"),
        "table": comp_table,
        "current_assessment": base_assessment_info,
        "comparison_assessment": comparison_assessment_info,
        "left_plot": Markup(  # noqa: MS001
            plot_risk_matrix(base_risks).replace(
                '<script', f'<script nonce="{request.csp_nonce}"'
            )
        ),
        "right_plot": Markup(  # noqa: MS001
            plot_risk_matrix(comarison_risks).replace(
                '<script', f'<script nonce="{request.csp_nonce}"'
            )
        ),
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

        return [
            Button(
                url=self.request.route_url(
                    "compare_assessments",
                    id_base=self.current_open_assessment().id,
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
    # category = DataColumn(_("Category"))
    asset_name = DataColumn(_("Asset"))
    likelihood = DataColumn(_("Likelihood"))
    diff_likelihood = DataColumn(_("Change (Likelihood)"))
    impact = DataColumn(_("Impact"))
    diff_impact = DataColumn(_("Change (Impact)"))

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

    display_name = StringField(label=_("Anzeigename"), validators=())
    end = DateTimeLocalField(
        label=_("Geschlossen per"),
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
    table = AssessImpactTable(context, request)
    return {
        "title": _("Assess Impact"),
        "table": table,
        "top_buttons": [],
    }


def assess_likelihood_view(
    context: "Organization", request: "IRequest"
) -> "RenderData":
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
    table = AssessmentOverviewTable(context, request)
    return {
        "title": _("Risk Matrix"),
        "plot": Markup(  # noqa: MS001
            plot_risk_matrix(table.query()).replace(
                '<script',
                f'<script nonce="{request.csp_nonce}"'
            )
        ),
        "table": table,
    }


def generate_risk_matrix_compare_view(
    context: "Organization", request: "IRequest"
) -> "RenderData":
    table = AssessmentOverviewTable(context, request)
    return {
        "title": _("Risk Matrix"),
        "plot": Markup(  # noqa: MS001
            plot_risk_matrix(table.query()).replace(
                '<script',
                f'<script nonce="{request.csp_nonce}"'
            )
        ),
        "table": table,
    }


def plot_risk_matrix(risks: 'Query[RiskMatrixAssessment]') -> str:
    fig = go.Figure()

    colors = {
        "green": [10, 15, 16, 20, 21, 22],
        "yellow": [0, 1, 5, 6, 7, 11, 12, 13,  17, 18, 19,  23, 24],
        "red": [3, 4, 8, 9, 14, 2],
    }

    for color, indices in colors.items():
        for index in indices:
            i, j = divmod(index, 5)
            fig.add_shape(
                type="rect",
                x0=j,
                y0=4 - i,
                x1=j + 1,
                y1=5 - i,
                line={"color": "rgba(0,0,0,0.5)", "width": 0.5},
                fillcolor=color,
                layer="below",
            )

    for risk in list(risks):
        if risk.likelihood and risk.impact:
            i = risk.nr
            y, x = risk.likelihood - 1, (risk.impact - 1)

            noise_x = np.random.uniform(0.1, 0.9)
            noise_y = np.random.uniform(0.1, 0.9)
            x, y = float(x) + noise_x, float(y) + noise_y

            fig.add_trace(
                go.Scatter(
                    x=[x],
                    y=[y],
                    text=[str(risk.nr)],
                    name="",
                    mode="markers+text",
                    marker={"color": "rgba(0,0,0,0.8)", "size": 18},
                    textposition="middle center",
                    hoverinfo="text",
                    hovertemplate=(
                        f"{risk.nr} {risk.name} "
                        f"(Impact: {risk.impact} "
                        f"Likelihood: {risk.likelihood})"
                    ),
                    textfont={"color": "rgba(0,0,0,0.9)"},
                )
            )

    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    # Create a clean base template without any default colors
    clean_template = go.layout.Template()

    fig.update_layout(
        xaxis={
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'range': [-0.5, 5]
        },
        yaxis={
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'range': [-0.5, 5]
        },
        showlegend=False,
        width=600,
        height=600,
        margin={'l': 5, 'r': 5, 't': 5, 'b': 5},
        template=clean_template,
        modebar={'bgcolor': 'rgba(0,0,0,0)', 'color': '#000000'},
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',   # Transparent background
        font={
            'color': '#000000',
            'family': 'DM Sans, sans-serif'
        }  # Default to black text
    )

    fig.add_annotation(
        x=2.5,
        y=-0.2,
        text="Impact",
        showarrow=False,
        font={
            'size': 20,
            'color': '#000000',
            'family': 'DM Sans, sans-serif'
        }
    )
    fig.add_annotation(
        x=-0.2,
        y=2.5,
        text="Likelihood",
        showarrow=False,
        textangle=-90,
        font={
            'size': 20,
            'color': '#000000',
            'family': 'DM Sans, sans-serif'
        }
    )

    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={
            "modeBarButtonsToRemove": ["zoom", "pan", "select", "lasso2d"],
            "displayModeBar": True,
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {
                "format": "svg",
                "filename": "risk_matrix",
            }
        }
    )


def finish_risk_assessment_view(
    context: "Organization",
    request: "IRequest"
) -> "MixedDataOrRedirect":
    if request.method == "GET":
        return {
            "title": _("Finish Risk Assessment"),
            "table": AssessmentInfoTable(context, request),
            "edit_form": AssessmentFinishForm(context, request),
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
        rules = (
            "-organization.users",
            "-organization.risks",
            "-organization.risk_catalogs",
            "-organization.assets",
            "-asset.assessments",
            "-asset.organization",
            "-risk.catalog.children",
            "-risk.catalog.parent",
            "-risk.catalog.risks",
            "-risk.catalog.organization",
            "-risk.assessments",
            "-risk.organization",
            "-risk_assessment_info"
        )
        entry.state_at_finish = json.dumps(entry.to_dict(rules=rules))
        request.dbsession.add(entry)
        request.dbsession.flush()

    assessment_finish_form = AssessmentFinishForm(context, request)

    for a in assessment:
        a.state = RiskAssessmentState.FINISHED
        a.name = assessment_finish_form.display_name.data
        if assessment_finish_form.end:
            a.finished_at = pytz.utc.localize(assessment_finish_form.end.data)
        else:
            a.finished_at = func.now()
        request.dbsession.add(a)
        request.dbsession.flush()

    new_assessment = RiskAssessmentInfo(
        organization_id=context.id
    )
    request.dbsession.add(new_assessment)
    request.dbsession.flush()

    for asset in context.assets:
        print("asset", asset.id)
        print("catalog_ids", asset.catalog_ids)
        for risk_catalog in filter(
            lambda c: c.id in asset.catalog_ids,
            context.risk_catalogs
        ):
            for risk in risk_catalog.risks:
                new_risk_assessment = RiskAssessment(
                    asset=asset,
                    risk=risk,
                    info=new_assessment
                )
                request.dbsession.add(new_risk_assessment)
                request.dbsession.flush()

    return HTTPFound(location=request.route_url("home"))


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
