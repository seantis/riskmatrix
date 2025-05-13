import re
from wtforms.validators import ValidationError

from riskmatrix.i18n import _


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from abc import abstractmethod
    from wtforms import Field
    from wtforms import Form


password_regex = re.compile(
    r'^(?=.{8,})(?=.*[a-z])(?=.*[A-Z])(?=.*[\d])(?=.*[\W]).*$'
)

email_regex = re.compile(
    r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
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


def email_validator(form: 'Form', field: 'Field') -> None:
    if not email_regex.match(field.data):
        raise ValidationError('Not a valid email.')


class Immutable:
    """
    This marker class is only useful as a common base class to the derived
    validators :class:`~riskmatrix.wtform.validators.Disabled` and
    :class:`~riskmatrix.wtform.validators.ReadOnly`.

    Our custom form class :class:`~riskmatrix.wtform.form.Form` will skip
    any fields that have a validator derived from this class when executing
    :meth:`Form.populate_obj() <riskmatrix.wtform.form.Form.populate_obj>`.
    """
    field_flags: dict[str, Any] = {}
    if TYPE_CHECKING:
        @abstractmethod
        def __call__(self, form: 'Form', field: 'Field') -> None: ...


class Disabled(Immutable):
    """
    Sets a field to disabled.

    Validation fails if formdata is supplied anyways.
    """

    def __init__(self) -> None:
        self.field_flags = {'disabled': True, 'aria_disabled': 'true'}

    def __call__(self, form: 'Form', field: 'Field') -> None:
        if field.raw_data is not None:
            raise ValidationError(_('This field is disabled.'))


class ReadOnly(Immutable):
    """
    Sets a field to disabled.

    Validation fails if formdata is supplied anyways.
    """

    def __init__(self) -> None:
        self.field_flags = {'readonly': True, 'aria_readonly': 'true'}

    def __call__(self, form: 'Form', field: 'Field') -> None:
        if field.data != field.object_data:
            raise ValidationError(_('This field is read only.'))
