from wtforms import StringField
from wtforms import validators
from wtforms import EmailField
from pyramid.httpexceptions import HTTPFound
from riskmatrix.i18n import _
from riskmatrix.wtform import Form
from riskmatrix.models import User
from markupsafe import Markup, escape

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..models import Organization
    from ..types import RenderDataOrRedirect, MixedDataOrRedirect


class AddUserForm(Form):
    def __init__(
        self,
        context: 'Organization',
        request: 'IRequest',
        prefix: str = 'add-user'
    ) -> None:
        super().__init__(
            request.POST,
            prefix=prefix,
            meta={
                'context': context,
                'request': request.dbsession
            }
        )
        self.title = _('Add User')

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

    email = EmailField(
        label=_('Email'),
        validators=[
            validators.InputRequired(),
            validators.Length(max=256),
            validators.Email(check_deliverability=False),
        ]
    )


def add_user_view(
    context: 'Organization',
    request: 'IRequest'
) -> 'MixedDataOrRedirect':
    form = AddUserForm(context, request)
    target_url = request.route_url('organization', id=context.id)

    if request.method == 'POST' and form.validate():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            organization=context
        )
        request.dbsession.add(user)
        message = _(
            'Successfully added user "${name}"',
            mapping={'name': f"{user.first_name} {user.last_name}"}
        )

        if request.is_xhr:
            request.dbsession.flush()
            request.dbsession.refresh(user)
            return {
                'data': [{
                    'first_name': escape(user.first_name),
                    'last_name': escape(user.last_name),
                    'email': escape(user.email),
                    'DT_RowId': f'row-{user.id}'
                }],
                'message': message,
            }
        else:
            request.messages.add(message, 'success')
            return HTTPFound(location=target_url)

    if request.is_xhr:
        return {'errors': form.errors}
    else:
        return {
            'form': form,
            'target_url': target_url,
        } 

