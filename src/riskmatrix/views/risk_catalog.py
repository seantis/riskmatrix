from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import validators

from riskmatrix.controls import Button
from riskmatrix.models import RiskCatalog
from riskmatrix.data_table import AJAXDataTable
from riskmatrix.data_table import DataColumn
from riskmatrix.data_table import maybe_escape
from riskmatrix.i18n import _
from riskmatrix.i18n import translate
from riskmatrix.static import xhr_edit_js
from riskmatrix.wtform import Form


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm.query import Query
    from typing import TypeVar
    from wtforms import Field

    from riskmatrix.models import Organization
    from riskmatrix.types import MixedDataOrRedirect
    from riskmatrix.types import XHRDataOrRedirect
    from riskmatrix.types import RenderData

    _Q = TypeVar('_Q', bound=Query[Any])


class RiskCatalogGenerationForm(Form):

    def __init__(
        self,
        context: RiskCatalog | None,
        request: 'IRequest',
        prefix:  str = 'generate-xhr'
    ) -> None:

        self.title = _("AI Assisted Risk Catalog Generation")

        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={
                'context': context,
                'request': request
            }
        )

    question_1 = StringField(
        label=_('In welchem Bereich agiert die Firma?'),
        validators=(
            validators.DataRequired(),
            validators.Length(max=256, min=2),
        )
    )

    question_2 = StringField(
        label=_('Bitte beschreibe deine Haupt-Kundenportolio in einem Satz'),
        validators=(
            validators.DataRequired(),
            validators.Length(max=256, min=2),
        )
    )

    question_3 = StringField(
        label=_('Was für IT Angelegenheiten werden durch externe Partner betrieben?'),
        validators=(
            validators.DataRequired(),
            validators.Length(max=256, min=2),
        )
    )


class RiskCatalogForm(Form):

    def __init__(
        self,
        context: RiskCatalog | None,
        request: 'IRequest',
        prefix:  str = 'edit-xhr'
    ) -> None:

        self.title = (
            _('Add Risk Catalog') if context is None else
            _('Edit Risk Catalog')
        )

        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={
                'context': context,
                'request': request
            }
        )

    name = StringField(
        label=_('Name'),
        validators=(
            validators.DataRequired(),
            validators.Length(max=256),
        )
    )

    description = TextAreaField(
        label=_('Description'),
        validators=(
            validators.Optional(),
        )
    )

    def validate_name(self, field: 'Field') -> None:
        session = self.meta.request.dbsession
        catalog = self.meta.context
        if catalog is None:
            organization_id = self.meta.request.user.organization_id
        else:
            organization_id = catalog.organization_id

        query = session.query(RiskCatalog.id)
        query = query.filter(RiskCatalog.name == field.data)
        query = query.filter(RiskCatalog.organization_id == organization_id)
        if catalog is not None:
            query = query.filter(RiskCatalog.id != catalog.id)
        if session.query(query.exists()).scalar():
            raise validators.ValidationError(_(
                'A risk catalog with this name already exists.'
            ))


def catalog_buttons(catalog: RiskCatalog, request: 'IRequest') -> list[Button]:
    return [
        Button(
            url=request.route_url('risks', id=catalog.id),
            icon='list',
            description=_('View Risks'),
            css_class='btn-sm btn-secondary',
        ),
        Button(
            url=request.route_url('edit_catalog', id=catalog.id),
            icon='edit',
            description=_('Edit Catalog'),
            css_class='btn-sm btn-secondary',
            modal='#edit-xhr',
        ),
        Button(
            url=request.route_url('delete_catalog', id=catalog.id),
            icon='trash',
            description=_('Delete'),
            css_class='btn-sm btn-danger',
            modal='#delete-xhr',
            data_item_title=catalog.name,
        )
    ]


class RiskCatalogTable(AJAXDataTable[RiskCatalog]):
    default_options = {
        'length_menu': [[25, 50, 100, -1], [25, 50, 100, 'All']],
        'order': [[0, 'asc']]  # corresponds to column name
    }

    name = DataColumn(_('Name'))
    description = DataColumn(_('Description'), class_name='visually-hidden')

    def __init__(self, org: 'Organization', request: 'IRequest') -> None:
        super().__init__(org, request, id='catalog-table')
        xhr_edit_js.need()

    def apply_static_filters(self, query: '_Q') -> '_Q':
        return query.filter(RiskCatalog.organization_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, '_total_records'):
            session = self.request.dbsession
            query = session.query(func.count(RiskCatalog.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def query(self) -> 'Query[RiskCatalog]':
        session = self.request.dbsession
        query = session.query(RiskCatalog)
        query = self.apply_static_filters(query)
        if self.order_by:
            query = query.order_by(
                getattr(getattr(RiskCatalog, self.order_by), self.order_dir)()
            )
        else:
            query = query.order_by(RiskCatalog.name.asc())
        return query

    def buttons(self, catalog: RiskCatalog | None = None) -> list[Button]:
        if catalog is None:
            return []

        return catalog_buttons(catalog, self.request)


def risk_catalog_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderData':

    table = RiskCatalogTable(context, request)
    return {
        'title': _('Risk Catalog'),
        'delete_title': _('Delete Risk Catalog'),
        'table': table,
        'top_buttons': [Button(
            url=request.route_url('add_catalog', id=context.id),
            icon='plus',
            title=_('Add Risk Catalog'),
            css_class='btn-primary',
            modal='#edit-xhr',
            data_table_id=table.id,
        ), Button(
            url=request.route_url('generate_catalog', id=context.id),
            icon='plus',
            title=_('AI Assisted Risk Catalog Generation'),
            css_class='btn-primary',
            modal='#generate-xhr',
            data_table_id=table.id,
        )],
        'edit_form': RiskCatalogForm(None, request),
        'generate_form': RiskCatalogGenerationForm(None, request),
        'helper_text': Markup("Risk catalogs are collections of risks to be combined with multiple different assets, looking for <a href=\"/assets\">assets</a>?")
    }


def delete_risk_catalog_view(
    context: RiskCatalog,
    request: 'IRequest'
) -> 'XHRDataOrRedirect':

    organization_id = context.organization_id
    name = context.name

    context.soft_delete()
    request.dbsession.flush()

    message = _(
        'Succesfully deleted risk catalog "${name}"',
        mapping={'name': name}
    )

    if request.is_xhr:
        return {'success': translate(message, request.locale_name)}

    request.messages.add(message, 'success')
    return HTTPFound(
        location=request.route_url('risk_catalog', id=organization_id)
    )


def edit_risk_catalog_view(
    context: 'RiskCatalog | Organization',
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    if isinstance(context, RiskCatalog):
        catalog = context
    else:
        catalog = None
        organization = context

    form = RiskCatalogForm(catalog, request)
    target_url = request.route_url('risk_catalog')
    if request.method == 'POST' and form.validate():
        if catalog is None:
            catalog = RiskCatalog(
                name=form.name.data or '',
                organization=organization
            )
            request.dbsession.add(catalog)
            message = _(
                'Succesfully added risk catalog "${name}"',
                mapping={'name': form.name.data}
            )
            if not request.is_xhr:
                request.messages.add(message, 'success')

        form.populate_obj(catalog)
        if request.is_xhr:
            data = {
                'name': maybe_escape(catalog.name),
                'description': maybe_escape(catalog.description),
            }
            if not isinstance(context, RiskCatalog):
                request.dbsession.flush()
                request.dbsession.refresh(catalog)
                data['DT_RowId'] = f'row-{catalog.id}'
                data['buttons'] = Markup(' ').join(
                    catalog_buttons(catalog, request)
                )
                data['message'] = translate(message, request.locale_name)
            return data
        else:
            return HTTPFound(location=target_url)
    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'target_url': target_url,
        }
