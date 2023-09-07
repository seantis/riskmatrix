import re
from wtforms.validators import ValidationError

from riskmatrix.i18n import _


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms import Field
    from wtforms import Form


password_regex = re.compile(
    r'^(?=.{8,})(?=.*[a-z])(?=.*[A-Z])(?=.*[\d])(?=.*[\W]).*$'
)


def password_validator(form: 'Form', field: 'Field') -> None:
    password = form['password'].data
    password_confirmation = form['password_confirmation'].data

    if not password or not password_confirmation:
        return

    if password != password_confirmation:
        raise ValidationError(_('Password and confirmation do not match.'))

    if not password_regex.match(password):
        msg = _(
            'Password must have minimal length of 8 characters, contain '
            'one upper case letter, one lower case letter, one digit and '
            'one special character.'
        )
        raise ValidationError(msg)
