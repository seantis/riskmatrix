from .transparent_form_field import TransparentFormField


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from wtforms import Field


def FieldList(**fields: 'Field') -> 'TransparentFormField[Any]':
    from ..form import Form

    form_class = type('TransparentForm', (Form,), fields)
    return TransparentFormField(form_class)


__all__ = (
    'FieldList',
    'TransparentFormField'
)
