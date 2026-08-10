import json
from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import func
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import validators
from pyramid.response import Response
from langchain_core.messages import HumanMessage

from riskmatrix.controls import Button
from riskmatrix.models import Risk
from riskmatrix.models import RiskCategory, RiskCatalog
from riskmatrix.data_table import AJAXDataTable
from riskmatrix.data_table import DataColumn
from riskmatrix.data_table import maybe_escape
from riskmatrix.i18n import _
from riskmatrix.i18n import translate
from riskmatrix.static import xhr_edit_js
from riskmatrix.views.risk_catalog import (
    RiskCatalogForm,
    RiskCatalogGenerationForm,
    RiskCatalogTable
)
from riskmatrix.wtform import Form
from riskmatrix.prompts import system_prompts, user_prompts, examples


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Iterator
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session
    from sqlalchemy.orm.query import Query
    from typing import TypeVar
    from wtforms import Field
    from wtforms.fields.choices import _Choice
    from wtforms.fields.choices import _GroupedChoices

    from riskmatrix.models.organization import Organization
    from riskmatrix.types import MixedDataOrRedirect
    from riskmatrix.types import XHRDataOrRedirect
    from riskmatrix.types import RenderData

    _Q = TypeVar('_Q', bound=Query[Any])


# FIXME: currently we only render the top-level and the leaves
#        since optgroup only supports one level of nesting, maybe
#        we should restrict categories to the same? However the
#        ISO example contains two levels of nesting...
def category_choices(
    organization_id: str,
    session: 'Session'
) -> 'list[_Choice] | _GroupedChoices':

    children_map: dict[str | None, list[tuple[str, str]]] = {}
    query = session.query(
        RiskCategory.id,
        RiskCategory.parent_id,
        RiskCategory.name,
    )
    query = query.filter(RiskCategory.organization_id == organization_id)
    query = query.order_by(RiskCategory.name.asc())
    for id, parent_id, name in query:
        children_map.setdefault(parent_id, []).append((id, name))

    if not children_map:
        return [('', '')]
    elif children_map.keys() == {None}:
        # we only have one level of categories
        return [(name, name) for __, name in children_map[None]]

    def walk_tree(nodes: list[tuple[str, str]]) -> 'Iterator[tuple[str, str]]':
        for node_id, name in nodes:
            children = children_map.get(node_id)
            if children is None:
                yield (name, name)
            else:
                yield from walk_tree(children)

    return {
        group_name: list(walk_tree(children))
        if (children := children_map.get(group_id))
        else [(group_name, group_name)]
        for group_id, group_name in children_map.get(None, [])
    }


class RiskMetaForm(Form):

    def __init__(
        self,
        context: Risk | RiskCatalog,
        request: 'IRequest',
        prefix:  str = 'edit-xhr'
    ) -> None:

        if isinstance(context, Risk):
            obj = context
            # organization_id = context.organization_id
            self.title = _('Edit Risk')
        else:
            obj = None
            # organization_id = context.id
            self.title = _('Add Risk')

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
        # FIXME: currently disabled due to complexity given another dimension
        # self.category.choices = category_choices(
        #    organization_id,
        #    session
        # )

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

    # FIXME: currently disabled due to complexity given another dimension
    # category = SelectField(
    #    label=_('Category'),
    #    choices=[('', '')],
    #    validators=(
    #        validators.Optional(),
    #    ),
    # )

    def validate_name(self, field: 'Field') -> None:
        session = self.meta.dbsession
        if isinstance(self.meta.context, Risk):
            risk = self.meta.context
            organization_id = risk.organization_id
        else:
            risk = None
            organization_id = self.meta.context.id
        name = field.data
        query = session.query(Risk.id)
        query = query.filter(Risk.name == name)
        query = query.filter(Risk.organization_id == organization_id)
        if risk is not None:
            query = query.filter(Risk.id != risk.id)
        if session.query(query.exists()).scalar():
            raise validators.ValidationError(_(
                'A risk with this name already exists.'
            ))


def risk_buttons(risk: Risk, request: 'IRequest') -> list[Button]:
    return [
        Button(
            url=request.route_url('edit_risk', id=risk.id),
            icon='edit',
            description=_('Edit Risk'),
            css_class='btn-sm btn-secondary',
            modal='#edit-xhr',
        ),
        Button(
            url=request.route_url('delete_risk', id=risk.id),
            icon='trash',
            description=_('Delete'),
            css_class='btn-sm btn-danger',
            modal='#delete-xhr',
            data_item_title=risk.name,
        )
    ]


class RisksTable(AJAXDataTable[Risk]):
    default_options = {
        'length_menu': [[25, 50, 100, -1], [25, 50, 100, 'All']],
        'order': [[0, 'asc']]  # corresponds to column name
    }

    name = DataColumn(_('Name'))
    # category = DataColumn(_('Category', ), class_name='visually-hidden')
    description = DataColumn(_('Description'))

    def __init__(self, catalog: RiskCatalog, request: 'IRequest') -> None:
        super().__init__(catalog, request, id='risks-table')
        xhr_edit_js.need()

    def apply_static_filters(self, query: '_Q') -> '_Q':
        return query.filter(Risk.catalog_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, '_total_records'):
            session = self.request.dbsession
            query = session.query(func.count(Risk.id))
            query = self.apply_static_filters(query)
            self._total_records: int = query.scalar()
        return self._total_records

    def query(self) -> 'Query[Risk]':
        session = self.request.dbsession
        query = session.query(Risk)
        query = self.apply_static_filters(query)
        if self.order_by:
            query = query.order_by(
                getattr(getattr(Risk, self.order_by), self.order_dir)()
            )
        else:
            query = query.order_by(Risk.name.asc())
        return query

    def buttons(self, risk: Risk | None = None) -> list[Button]:
        if risk is None:
            return []

        return risk_buttons(risk, self.request)


def risks_view(context: RiskCatalog, request: 'IRequest') -> 'RenderData':
    table = RisksTable(context, request)
    return {
        'supertitle': _('Risks', mapping={'catalog': context.name}),
        'title': _('${catalog}', mapping={'catalog': context.name}),
        'description': _(
            '${catalog}',
            mapping={'catalog': context.description}
        ),
        'delete_title': _('Delete Risk'),
        'table': table,
        'top_buttons': [Button(
            url=request.route_url('add_risk', id=context.id),
            icon='plus',
            title=_('Add Risk'),
            css_class='btn-primary',
            modal='#edit-xhr',
            data_table_id=table.id,
        )],
        'edit_form': RiskMetaForm(context, request),
    }


def delete_risk_view(
    context: Risk,
    request: 'IRequest'
) -> 'XHRDataOrRedirect':

    catalog_id = context.catalog_id
    name = context.name

    context.soft_delete()
    request.dbsession.flush()

    message = _(
        'Succesfully deleted risk "${name}"',
        mapping={'name': name}
    )

    if request.is_xhr:
        return {'success': translate(message, request.locale_name)}

    request.messages.add(message, 'success')
    return HTTPFound(location=request.route_url('risks', id=catalog_id))


def edit_risk_view(
    context: Risk | RiskCatalog,
    request: 'IRequest'
) -> 'MixedDataOrRedirect':
    if isinstance(context, Risk):
        risk = context
        organization_id = context.organization_id
    else:
        risk = None
        try:
            if request.json:
                risk = Risk(
                    name=request.json["name"],
                    description=request.json["description"],
                    catalog=context
                )
                request.dbsession.add(risk)
                request.dbsession.flush()
                request.dbsession.refresh(risk)
                response = Response(status=201)

                return response
        except Exception as e:
            print(e)
        organization_id = context.id
        catalog = context
    form = RiskMetaForm(context, request)
    target_url = request.route_url('risks', id=organization_id)
    try:
        t = request.json
        has_json = t is not None
    except Exception as e:
        print(e)
        has_json = False
    if request.method == 'POST' and (not has_json and form.validate()):
        if risk is None:
            risk = Risk(name=form.name.data or '', catalog=catalog)
            request.dbsession.add(risk)
            message = _(
                'Succesfully added risk "${name}"',
                mapping={'name': risk.name}
            )
            if not request.is_xhr:
                request.messages.add(message, 'success')

        form.populate_obj(risk)
        if request.is_xhr:
            data = {
                'name': maybe_escape(risk.name),
                'description': maybe_escape(risk.description),
                'category': maybe_escape(risk.category),
            }
            if not isinstance(context, Risk):
                request.dbsession.flush()
                request.dbsession.refresh(risk)
                data['DT_RowId'] = f'row-{risk.id}'
                data['buttons'] = Markup(' ').join(risk_buttons(risk, request))
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


def stream_risk_generation(
    context: 'Organization',
    request: 'IRequest'
) -> Any:
    req_catalog = request.json['catalog']
    existing_catalog: RiskCatalog | None = (
        request.dbsession.query(RiskCatalog)
        .filter_by(name=req_catalog['name'], organization_id=context.id)
        .first()
    )
    if existing_catalog:
        catalog = existing_catalog
    else:
        catalog = RiskCatalog(
            name=req_catalog['name'],
            organization=context,
            description=req_catalog['description']
        )
        request.dbsession.add(catalog)
        request.dbsession.flush()
        request.dbsession.refresh(catalog)

    def generate(
        catalog_name: str,
        catalog_description: str,
        email: str,
        org_name: str
    ) -> Any:
        answers = request.json['answers']
        user_answers = '\n'.join([
            f' - **{answer[0]}**: {answer[1]}'
            for answer in answers.items()
        ])
        risk_examples = '\n'.join([
            f' - __{answer["name"]}__: {answer["description"]}'
            for answer in examples['risks']
        ])
        prompt = (
            f"{system_prompts['risks']}\n"
            f"\n{user_prompts['risks']}\n"
            f"Examples:\n{risk_examples}\n\n"
            f"User-Answers:\n{user_answers}. \n\n"
            f"Current Risk-Catalog:\n"
            f" - name:{catalog_name}\n"
            f" - description: {catalog_description}"
        )
        try:
            messages = [
                HumanMessage(content=prompt)
            ]
            config = {
                "callbacks": [request.langfuse],
                "langfuse_user_id": email,
                "tags": [org_name]
            }
            response = request.llm.stream(messages, config=config)
            for event in response:
                yield bytes(event.content, encoding='utf-8')
        except Exception as e:
            raise StopIteration from e

    headers = [('Content-Type', 'text/event-stream'),
               ('Cache-Control', 'no-cache'),]
    response = Response(headerlist=headers)
    response.app_iter = generate(
        catalog.name,
        catalog.description,
        request.user.email,
        context.name
    )
    return response


def generate_risk_completion(
    context: 'Organization',
    request: 'IRequest'
) -> 'XHRDataOrRedirect':
    answers_form = RiskCatalogGenerationForm(None, request)

    answers = {
        field.label.text: field.data
        for field in (
            answers_form.question_1,
            answers_form.question_2,
            answers_form.question_3
        )
    }

    table = RiskCatalogTable(context, request)

    catalogs = list(examples['catalogs'])

    for idx, catalog in enumerate(catalogs):
        existing_catalog: RiskCatalog | None = (
            request.dbsession.query(RiskCatalog)
            .filter_by(name=catalog['name'], organization_id=context.id)
            .first()
        )
        if existing_catalog:
            catalogs[idx] = existing_catalog
        else:
            catalog = RiskCatalog(
                name=catalog['name'],
                organization=context,
                description=catalog['description']
            )
            request.dbsession.add(catalog)
            request.dbsession.flush()
            request.dbsession.refresh(catalog)
            catalogs[idx] = catalog

    # catalogs as list of dict using fields name, id and description
    catalogs = [
        {
            'name': catalog.name,
            'description': catalog.description,
            'id': catalog.id
        } for catalog in catalogs
    ]

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
        'generate_form': answers_form,
        'risk_catalogs': json.dumps(catalogs),
        'answers': json.dumps(answers)
    }
