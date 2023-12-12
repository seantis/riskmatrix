from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import validators

from riskmatrix.controls import Button
from riskmatrix.models import Asset
from riskmatrix.models import Risk
from riskmatrix.models import RiskAssessment
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
    from sqlalchemy.orm import Session
    from sqlalchemy.orm.query import Query
    from typing import TypeVar
    from wtforms import Field
    from wtforms.fields.choices import _Choice

    from riskmatrix.models import Organization
    from riskmatrix.types import MixedDataOrRedirect
    from riskmatrix.types import XHRDataOrRedirect
    from riskmatrix.types import RenderData

    _Q = TypeVar('_Q', bound=Query[Any])


# NOTE: Eventually this should return a nested dict to represent
#       the nested risk catalog tree
def catalog_choices(
    organization_id: str,
    session: 'Session'
) -> list['_Choice']:

    query = session.query(
        RiskCatalog.id,
        RiskCatalog.name,
    )
    query = query.filter(RiskCatalog.organization_id == organization_id)
    query = query.order_by(RiskCatalog.name.asc())

    return [
        (catalog_id, catalog_name)
        for catalog_id, catalog_name in query
    ]


class AssetForm(Form):

    def __init__(
        self,
        context: 'Organization | Asset',
        request: 'IRequest',
        prefix:  str = 'edit-xhr'
    ) -> None:

        if isinstance(context, Asset):
            obj = context
            organization_id = context.organization_id
            self.title = _('Edit Asset')
        else:
            obj = None
            organization_id = context.id
            self.title = _('Add Asset')

        session = request.dbsession
        super().__init__(
            request.POST,
            obj=obj,
            prefix=prefix,
            meta={
                'context': context,
                'dbsession': session
            }
        )

        self.catalog_ids.choices = catalog_choices(
            organization_id,
            session
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

    # TODO: Create a nested checkbox field
    catalog_ids = SelectMultipleField(
        label=_('Risk Catalogs'),
        choices=[('', '')],
        validators=(
            validators.Optional(),
        )
    )

    def populate_obj(self, obj: Asset) -> None:  # type:ignore[override]
        super().populate_obj(obj)

        existing_risk_ids = {
            assessment.risk.id
            for assessment in obj.assessments
        }
        new_risk_ids = set()

        session = self.meta.dbsession
        query = session.query(Risk)
        query = query.filter(Risk.catalog_id.in_(obj.catalog_ids))
        for risk in query:
            new_risk_ids.add(risk.id)
            if risk.id not in existing_risk_ids:
                # create an empty assessment
                session.add(RiskAssessment(obj, risk))

        # remove empty assessments that are no longer relevant
        for assessment in obj.assessments:
            if assessment.risk_id in new_risk_ids:
                continue

            if assessment.modified is None:
                session.delete(assessment)

    def validate_name(self, field: 'Field') -> None:
        session = self.meta.dbsession
        context = self.meta.context
        if isinstance(context, Asset):
            asset = context
            organization_id = asset.organization_id
        else:
            asset = None
            organization_id = context.id

        query = session.query(Asset.id)
        query = query.filter(Asset.name == field.data)
        query = query.filter(Asset.organization_id == organization_id)
        if asset is not None:
            query = query.filter(Asset.id != asset.id)
        if session.query(query.exists()).scalar():
            raise validators.ValidationError(_(
                'An asset with this name already exists.'
            ))


def catalog_buttons(asset: Asset, request: 'IRequest') -> list[Button]:
    return [
        Button(
            url=request.route_url('edit_asset', id=asset.id),
            icon='edit',
            description=_('Edit Asset'),
            css_class='btn-sm btn-secondary',
            modal='#edit-xhr',
        ),
        Button(
            url=request.route_url('delete_asset', id=asset.id),
            icon='trash',
            description=_('Delete'),
            css_class='btn-sm btn-danger',
            modal='#delete-xhr',
            data_item_title=asset.name,
        )
    ]


class AssetTable(AJAXDataTable[Asset]):
    default_options = {
        'length_menu': [[25, 50, 100, -1], [25, 50, 100, 'All']],
        'order': [[0, 'asc']]  # corresponds to column name
    }

    name = DataColumn(_('Name'))
    description = DataColumn(_('Description'), class_name='visually-hidden')
    catalog_ids = DataColumn(
        _('Risk Catalogs'),
        # FIXME: We should encode this as JSON and deal with it in edit-xhr
        #        for now we'll treat it like a single-select and only include
        #        the first selection
        format_data=lambda d: d[0] if d else '',
        class_name='visually-hidden'
    )

    def __init__(self, org: 'Organization', request: 'IRequest') -> None:
        super().__init__(org, request, id='asset-table')
        xhr_edit_js.need()

    def apply_static_filters(self, query: '_Q') -> '_Q':
        return query.filter(Asset.organization_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, '_total_records'):
            session = self.request.dbsession
            query = session.query(func.count(Asset.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def query(self) -> 'Query[Asset]':
        session = self.request.dbsession
        query = session.query(Asset)
        query = self.apply_static_filters(query)
        if self.order_by:
            query = query.order_by(
                getattr(getattr(Asset, self.order_by), self.order_dir)()
            )
        else:
            query = query.order_by(Asset.name.asc())
        return query

    def buttons(self, asset: Asset | None = None) -> list[Button]:
        if asset is None:
            return []

        return catalog_buttons(asset, self.request)


def assets_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderData':

    table = AssetTable(context, request)
    return {
        'title': _('Assets'),
        'delete_title': _('Delete Asset'),
        'table': table,
        'top_buttons': [Button(
            url=request.route_url('add_asset', id=context.id),
            icon='plus',
            title=_('Add Asset'),
            css_class='btn-primary',
            modal='#edit-xhr',
            data_table_id=table.id,
        )],
        'edit_form': AssetForm(context, request),
    }


def delete_asset_view(
    context: Asset,
    request: 'IRequest'
) -> 'XHRDataOrRedirect':

    organization_id = context.organization_id
    name = context.name

    session = request.dbsession
    session.delete(context)
    session.flush()

    message = _(
        'Succesfully deleted asset "${name}"',
        mapping={'name': name}
    )

    if request.is_xhr:
        return {'success': translate(message, request.locale_name)}

    request.messages.add(message, 'success')
    return HTTPFound(
        location=request.route_url('risk_catalog', id=organization_id)
    )


def edit_asset_view(
    context: 'Asset | Organization',
    request: 'IRequest'
) -> 'MixedDataOrRedirect':

    if isinstance(context, Asset):
        asset = context
    else:
        asset = None
        organization = context

    form = AssetForm(context, request)
    target_url = request.route_url('assets')
    if request.method == 'POST' and form.validate():
        if asset is None:
            asset = Asset(
                name=form.name.data or '',
                organization=organization
            )
            request.dbsession.add(asset)
            message = _(
                'Succesfully added asset "${name}"',
                mapping={'name': form.name.data}
            )
            if not request.is_xhr:
                request.messages.add(message, 'success')

        form.populate_obj(asset)
        if request.is_xhr:
            data = {
                'name': maybe_escape(asset.name),
                'description': maybe_escape(asset.description),
                # FIXME: same as above we should encode this
                'catalog_ids': (
                    asset.catalog_ids[0] if asset.catalog_ids else ''
                )
            }
            if not isinstance(context, Asset):
                request.dbsession.flush()
                request.dbsession.refresh(asset)
                data['DT_RowId'] = f'row-{asset.id}'
                data['buttons'] = Markup(' ').join(
                    catalog_buttons(asset, request)
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
