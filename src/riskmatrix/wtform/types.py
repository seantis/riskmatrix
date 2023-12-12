from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, TypeVar
    from typing_extensions import TypeAlias

    from wtforms import Field, Form
    from wtforms.fields.core import _Validator

    FormT = TypeVar('FormT', bound=Form, contravariant=True)
    FieldT = TypeVar('FieldT', bound=Field, contravariant=True)
    Validators: TypeAlias = tuple[_Validator[FormT, FieldT], ...] | list[Any]
