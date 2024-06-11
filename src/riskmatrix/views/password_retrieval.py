import logging
from email.headerregistry import Address
from pyramid.httpexceptions import HTTPFound
from wtforms import Form
from wtforms import StringField
from wtforms.validators import InputRequired

from ..mail import IMailer
from ..models import PasswordChangeToken
from ..models import User
from ..security_policy import PasswordException
from ..wtform.validators import email_validator


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session
    from ..types import RenderDataOrRedirect

logger = logging.getLogger('certificateclaim.auth')


class PasswordRetrievalForm(Form):

    email = StringField(
        label='Email',
        validators=[
            InputRequired(),
            email_validator
        ]
    )


def expire_all_tokens(user: User, session: 'Session') -> None:
    query = session.query(PasswordChangeToken)
    query = query.filter(PasswordChangeToken.user_id == user.id)
    query = query.filter(PasswordChangeToken.time_expired.is_(None))
    for token in query:
        token.expire()


def mail_retrieval(email: str, request: 'IRequest') -> None:
    # NOTE: This will probably get caught by email_validator
    #       but lets just be safe for now...
    if '\x00' in email:
        raise PasswordException(f'Invalid email "{email}"')

    session = request.dbsession
    query = session.query(User)
    query = query.filter(User.email.ilike(email))
    user = query.first()
    if not user:
        raise PasswordException(f'User "{email}" not found')

    expire_all_tokens(user, session)
    ip_address = getattr(request, 'client_addr', '')
    token_obj = PasswordChangeToken(user, ip_address)
    session.add(token_obj)
    session.flush()

    mailer = request.registry.getUtility(IMailer)
    mailer.send_template(
        sender=None,  # This mail doesn't need a reply-to
        receivers=Address(user.fullname, addr_spec=user.email),
        template='password-reset',
        data={
            'name': user.fullname,
            'action_url': request.route_url(
                'password_change',
                _query={'token': token_obj.token}
            )
        },
        tag='password-reset',
    )


def password_retrieval_view(request: 'IRequest') -> 'RenderDataOrRedirect':
    form = PasswordRetrievalForm(formdata=request.POST)
    if 'email' in request.POST and form.validate():
        try:
            assert form.email.data is not None
            email = form.email.data.lower()
            mail_retrieval(email, request)
            logger.info(f'Password retrieval mail sent to "{email}"')
        except PasswordException as e:
            logger.warning(
                f'[{request.client_addr}] password retrieval: {str(e)}'
            )

        request.messages.add(
            'An email has been sent to the requested account with further '
            'information. If you do not receive an email then please '
            'confirm you have entered the correct email address.',
            'success'
        )
        return HTTPFound(location=request.route_url('login'))

    return {'form': form}