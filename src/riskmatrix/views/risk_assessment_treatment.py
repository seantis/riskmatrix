from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
import sqlalchemy.orm
from wtforms import StringField, TextAreaField, SelectField, FieldList
from wtforms.widgets import ListWidget, TextInput
from wtforms import validators

from riskmatrix.controls import Button
from riskmatrix.models import RiskAssessment
from riskmatrix.models.risk_assessment_info import RiskAssessmentInfo
from riskmatrix.models.risk_assessment_treatment import RiskAssessmentTreatment, TreatmentType
from riskmatrix.data_table import AJAXDataTable
from riskmatrix.data_table import DataColumn
from riskmatrix.data_table import maybe_escape
from riskmatrix.i18n import _
from riskmatrix.static import xhr_edit_js
from riskmatrix.wtform import Form


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


class LinksField(FieldList):
    widget = ListWidget(prefix_label=False)

    def __init__(self, **kwargs):
        super().__init__(
            StringField(widget=TextInput()),
            min_entries=1,
            **kwargs
        )


class TreatmentForm(Form):
    title = _("Edit Risk Treatment")

    def __init__(
        self,
        context: RiskAssessment | None,
        request: "IRequest",
        prefix: str = "edit-xhr",
    ) -> None:
        session = request.dbsession
        super().__init__(
            request.POST,
            obj=context.treatment if context and context.treatment else None,
            prefix=prefix,
            meta={"context": context, "dbsession": session},
        )

    description = TextAreaField(
        label=_("Description"),
        validators=[validators.Optional()]
    )

    links = LinksField(label=_("Links"))

    treatment_type = SelectField(
        label=_("Treatment Type"),
        choices=[
            (t.name, str(t)) for t in TreatmentType
        ],
        validators=[validators.DataRequired()]
    )

    post_likelihood = SelectField(
        label=_("Post-Treatment Likelihood"),
        choices=[(str(i), str(i)) for i in range(1, 6)],
        validators=[validators.Optional()],
        coerce=int
    )

    post_impact = SelectField(
        label=_("Post-Treatment Impact"),
        choices=[(str(i), str(i)) for i in range(1, 6)],
        validators=[validators.Optional()],
        coerce=int
    )


class TreatmentTable(AJAXDataTable[RiskAssessment]):
    default_options = {
        "length_menu": [[10, 25, 50, -1], [10, 25, 50, "All"]],
        "order": [[0, "asc"]],
        "search": {"regex": False},
        "processing": True,
        "language": {"url": "/static/json/dataTables.de.json"}
    }

    name = DataColumn(_("Name"))
    description = DataColumn(_("Description"))
    likelihood = DataColumn(_("Pre-Treatment Likelihood"))
    impact = DataColumn(_("Pre-Treatment Impact"))
    treatment_type = DataColumn(
        _("Treatment Type"),
        format_data=lambda assessment: (
            str(assessment.treatment.treatment_type)
            if assessment.treatment else "-"
        )
    )

    def __init__(self, org: "Organization", request: "IRequest") -> None:
        super().__init__(org, request, id="treatment-table")
        xhr_edit_js.need()

    def apply_static_filters(self, query: "_Q") -> "_Q":
        return query.filter(RiskAssessment.organization_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, "_total_records"):
            session = self.request.dbsession
            query = session.query(func.count(RiskAssessment.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def matches_search(self, row: RiskAssessment) -> bool:
        if not self.search:
            return True
            
        search_text = self.search.lower()
        # Search in name and description
        if search_text in row.name.lower():
            return True
        if row.risk.description and search_text in row.risk.description.lower():
            return True
        return False

    def query(self) -> "Query[RiskAssessment]":
        session = self.request.dbsession
        
        # Get the latest risk assessment info
        latest_assessment = (
            session.query(RiskAssessmentInfo)
            .filter(RiskAssessmentInfo.organization_id == self.context.id)
            .order_by(RiskAssessmentInfo.created.desc())
            .first()
        )
        
        if not latest_assessment:
            return []
        
        # Base query for risk assessments with proper joins and eager loading
        query = (
            session.query(RiskAssessment)
            .join(RiskAssessment.risk)  # Join with risk table first
            .join(RiskAssessment.risk_assessment_info)  # Then join with info
            .outerjoin(RiskAssessment.treatment)  # Outer join with treatment since it's optional
            .filter(RiskAssessment.organization_id == self.context.id)
            .filter(RiskAssessment.risk_assessment_info_id == latest_assessment.id)
            .options(
                sqlalchemy.orm.joinedload(RiskAssessment.risk),
                sqlalchemy.orm.joinedload(RiskAssessment.risk_assessment_info),
                sqlalchemy.orm.joinedload(RiskAssessment.treatment)
            )
        )
        
        if self.order_by:
            column = getattr(RiskAssessment, self.order_by)
            query = query.order_by(getattr(column, self.order_dir)())
        else:
            query = query.order_by(RiskAssessment.name.asc())
            
        return query

    def buttons(self, assessment: RiskAssessment | None = None) -> list[Button]:
        if assessment is None:
            return []

        return [
            Button(
                url=self.request.route_url("edit_treatment", id=assessment.id),
                icon="edit",
                description=_("Edit Treatment"),
                css_class="btn-sm btn-secondary",
                modal="#edit-xhr",
            )
        ]


def treatment_view(context: "Organization", request: "IRequest") -> "RenderData":
    table = TreatmentTable(context, request)
    return {
        "title": _("Plan Treatment"),
        "table": table,
        "edit_form": TreatmentForm(None, request),
    }


def edit_treatment_view(
    context: RiskAssessment,
    request: "IRequest"
) -> "MixedDataOrRedirect":
    form = TreatmentForm(context, request)
    organization_id = context.risk.organization_id
    target_url = request.route_url("treatment", id=organization_id)

    if request.method == "POST":
        # Extract links from form data
        links = []
        for key, value in request.POST.items():
            if key.startswith('links-') and value.strip():
                links.append(value.strip())

        # Create or get treatment
        if not context.treatment:
            context.treatment = RiskAssessmentTreatment(context)
            request.dbsession.add(context.treatment)

        # Update treatment type if provided
        if 'treatment_type' in request.POST and request.POST['treatment_type']:
            try:
                context.treatment.treatment_type = TreatmentType[request.POST['treatment_type']]
            except KeyError:
                # Invalid treatment type provided
                if request.is_xhr:
                    return {"errors": {"treatment_type": ["Invalid treatment type"]}}
                return HTTPFound(location=target_url)

        # Update description if provided
        if 'description' in request.POST:
            context.treatment.description = request.POST['description']

        # Update links
        context.treatment.links = links

        # Update post assessment values if provided
        if 'post_likelihood' in request.POST:
            try:
                context.treatment.post_likelihood = int(request.POST['post_likelihood'])
            except (ValueError, TypeError):
                context.treatment.post_likelihood = None

        if 'post_impact' in request.POST:
            try:
                context.treatment.post_impact = int(request.POST['post_impact'])
            except (ValueError, TypeError):
                context.treatment.post_impact = None

        try:
            request.dbsession.add(context.treatment)
            request.dbsession.flush()
            request.dbsession.refresh(context.treatment)

            if request.is_xhr:
                return {
                    "name": maybe_escape(context.name),
                    "likelihood": context.likelihood,
                    "impact": context.impact,
                    "treatment_type": str(context.treatment.treatment_type),
                    "success": True
                }
            else:
                request.session.flash('Treatment updated successfully', 'success')
                return HTTPFound(location=target_url)

        except Exception as e:
            request.dbsession.rollback()
            if request.is_xhr:
                return {"errors": {"general": [str(e)]}}
            request.session.flash('Error updating treatment: ' + str(e), 'error')
            return HTTPFound(location=target_url)

    if request.is_xhr:
        return {"errors": form.errors}
    else:
        return {
            "form": form,
            "target_url": target_url,
        } 