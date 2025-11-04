from babel import Locale
from wtforms import RadioField
from wtforms import StringField
from wtforms import validators
from wtforms import BooleanField
from wtforms import PasswordField
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from riskmatrix.i18n import _
from riskmatrix.wtform import Form
from riskmatrix.views.table import Button
from riskmatrix.data_table import AJAXDataTable, DataColumn
from riskmatrix.models import User, Organization
from markupsafe import Markup
from .user import AddUserForm
from riskmatrix.static import xhr_edit_js

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..models import Organization
    from ..types import RenderDataOrRedirect, MixedDataOrRedirect
    from sqlalchemy.orm import Query


class UserTable(AJAXDataTable[User]):
    default_options = {
        'length_menu': [[10, 25, 50, -1], [10, 25, 50, 'All']],
        'order': [[0, 'asc']],
        'search': {'regex': False},
        'processing': True,
        'serverSide': True,
        'columns': [
            {'data': 'first_name'},
            {'data': 'last_name'},
            {'data': 'email'}
        ]
    }

    first_name = DataColumn(
        _('First Name'),
        data_name='first_name',
        sortable=True,
    )

    last_name = DataColumn(
        _('Last Name'),
        data_name='last_name',
        sortable=True,
    )

    email = DataColumn(
        _('Email'),
        data_name='email',
        sortable=True,
    )

    def __init__(self, org: 'Organization', request: 'IRequest') -> None:
        super().__init__(org, request, id='users-table')
        xhr_edit_js.need()
        # Set the AJAX URL after initialization
        self.default_options['ajax'] = {
            'url': request.route_url('organization', id=org.id)
        }

    def apply_static_filters(self, query: 'Query[User]') -> 'Query[User]':
        return query.filter(User.organization_id == self.context.id)

    def total_records(self) -> int:
        if not hasattr(self, '_total_records'):
            session = self.request.dbsession
            query = session.query(User.id)
            query = self.apply_static_filters(query)
            self._total_records: int = query.count()
        return self._total_records

    def query(self) -> 'Query[User]':
        session = self.request.dbsession
        query = session.query(User)
        query = self.apply_static_filters(query)
        
        if self.order_by:
            column = getattr(User, self.order_by)
            query = query.order_by(getattr(column, self.order_dir)())
        else:
            query = query.order_by(User.first_name.asc())
            
        return query

    def format_row(self, user: User) -> dict:
        return {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'DT_RowId': f'row-{user.id}'
        }

    def json(self) -> dict:
        query = self.query()
        total = self.total_records()
        
        # Apply search if present
        if self.search:
            query = query.filter(
                User.first_name.ilike(f'%{self.search}%') |
                User.last_name.ilike(f'%{self.search}%') |
                User.email.ilike(f'%{self.search}%')
            )
        
        # Get filtered count
        filtered = query.count()
        
        # Apply pagination
        if self.length > 0:
            query = query.offset(self.start).limit(self.length)
        
        # Format data
        data = [self.format_row(user) for user in query]
        
        return {
            'draw': self.draw,
            'recordsTotal': total,
            'recordsFiltered': filtered,
            'data': data
        }


class EditOrganizationForm(Form):

    def __init__(
        self,
        context: 'Organization',
        request: 'IRequest',
        prefix:  str = 'edit-organization'
    ) -> None:

        super().__init__(
            request.POST,
            obj=context,
            prefix=prefix,
            meta={
                'context': context,
                'request': request.dbsession
            }
        )

        locale = Locale.parse(request.locale_name)
        settings = request.registry.settings
        languages = settings.get('pyramid.available_languages', '').split()

        self.locale.choices = [
            (
                language,
                Locale.parse(language).get_language_name(locale) or language
            )
            for language in languages
        ]

    name = StringField(
        label=_('Name'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
        ]
    )

    email = StringField(
        label=_('E-Mail'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
            validators.Email(check_deliverability=False),
        ]
    )

    locale = RadioField(
        label=_('Language'),
        choices=[('en', 'English')],
        validators=[
            validators.InputRequired(),
        ]
    )


class CreateOrganizationForm(Form):
    def __init__(
        self,
        request: 'IRequest',
        prefix: str = 'create-organization'
    ) -> None:
        super().__init__(
            request.POST,
            prefix=prefix,
            meta={
                'request': request.dbsession
            }
        )
        self.title = _('Create Organization')

    name = StringField(
        label=_('Organization Name'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
        ]
    )

    email = StringField(
        label=_('Organization Email'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
            validators.Email(),
        ]
    )

    first_name = StringField(
        label=_('First Name'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
        ]
    )

    last_name = StringField(
        label=_('Last Name'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
        ]
    )

    initial_user_email = StringField(
        label=_('Email'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
            validators.Email(),
        ]
    )

    password = PasswordField(
        label=_('Password'),
        validators=[
            validators.InputRequired(),
            validators.Length(min=8),
        ]
    )

    def validate(self):
        if not super().validate():
            return False
        
        # All fields are now required by default, so no additional validation needed
        return True


def organization_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'RenderDataOrRedirect':

    form = EditOrganizationForm(context, request)
    target_url = request.route_url('organization', id=context.id)
    
    if request.method == 'POST' and form.validate():
        form.populate_obj(context)
        if request.is_xhr:
            return {'redirect_to': target_url}
        else:
            return HTTPFound(location=target_url)
            
    if request.is_xhr:
        if 'draw' in request.GET:
            # This is a DataTables AJAX request
            user_table = UserTable(context, request)
            return user_table.json()
        return {'errors': form.errors}
    else:
        user_table = UserTable(context, request)
        return {
            'title': _('Organization'),
            'form': form,
            'target_url': target_url,
            'csrf_token': request.session.get_csrf_token(),
            'table': user_table,
            'edit_form': AddUserForm(context, request),
            'top_buttons': [Button(
                url=request.route_url('add_user', id=context.id),
                icon='plus',
                title=_('Add User'),
                css_class='btn-primary',
                modal='#edit-xhr',
                data_table_id=user_table.id,
            )],
        }


def create_organization_view(
    request: 'IRequest'
) -> 'MixedDataOrRedirect':
    form = CreateOrganizationForm(request)
    target_url = request.route_url('home')

    if request.method == 'POST' and form.validate():
        organization = Organization(
            name=form.name.data,
            email=form.email.data,
            locale=request.locale_name
        )
        request.dbsession.add(organization)
        
        # Create new initial user
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.initial_user_email.data,
            organization=organization
        )
        request.dbsession.add(user)
        request.dbsession.flush()  # Flush to get the user ID
        
        # Set password for the user
        user.set_password(form.password.data)

        message = _(
            'Successfully created organization "${name}"',
            mapping={'name': organization.name}
        )

        if request.is_xhr:
            return {
                'redirect_to': target_url,
                'message': message,
            }
        else:
            request.messages.add(message, 'success')
            # Log the user in
            headers = remember(request, user.id)
            return HTTPFound(location=target_url, headers=headers)

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'title': _('Create Organization'),
            'form': form,
            'target_url': target_url,
        }
