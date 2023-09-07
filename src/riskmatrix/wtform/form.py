from functools import partial
from markupsafe import Markup
from wtforms import Form as BaseForm
from wtforms import Label
from wtforms.meta import DefaultMeta

from riskmatrix.i18n import pluralize
from riskmatrix.i18n import translate

from .fields import TransparentFormField


from typing import Any, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, MutableMapping, Sequence
    from wtforms import Field
    from wtforms.fields.core import UnboundField
    from wtforms.form import BaseForm as _BaseForm
    from wtforms.meta import _MultiDictLike

    _FieldT = TypeVar('_FieldT', bound=Field)


def update_field_class(
    field: 'Field',
    original_post_validate: 'Callable[[_BaseForm, bool], Any]',
    form: '_BaseForm',
    validation_stopped: bool
) -> None:

    original_post_validate(form, validation_stopped)
    if field.errors:
        field.render_kw['class'] += ' is-invalid'


class PyramidTranslations:
    def gettext(self, string: str) -> str:
        return translate(string)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return pluralize(singular, plural, n)


class BootstrapMeta(DefaultMeta):

    def bind_field(
        self,
        form:          '_BaseForm',
        unbound_field: 'UnboundField[_FieldT]',
        options:       'MutableMapping[str, Any]'
    ) -> '_FieldT':
        # NOTE: This adds bootstrap specific field classes to render_kw
        render_kw = unbound_field.kwargs.get('render_kw', {})
        field_type = unbound_field.field_class.__name__
        if field_type in ('SelectField', 'SelectMultipleField'):
            css_class = 'form-select'
        else:
            css_class = 'form-control'

        if 'class' in render_kw:
            css_class += f" {render_kw['class']}"

        render_kw['class'] = css_class
        options['render_kw'] = render_kw
        field = unbound_field.bind(form=form, **options)
        field.post_validate = partial(  # type:ignore[method-assign]
            update_field_class,
            field,
            field.post_validate
        )
        if not isinstance(field, TransparentFormField):
            field.label = BootstrapLabel(field.label, field.description)
        return field

    # NOTE: We implement this so we can provide translations for the
    #       errors from the wtforms builtin validators
    def get_translations(self, form: '_BaseForm') -> PyramidTranslations:
        return PyramidTranslations()


class BootstrapLabel(Label):

    def __init__(self, base_label: Label, description: str):
        self.field_id = base_label.field_id
        self.text = base_label.text
        self.description = description

    def __call__(self, text: str | None = None, **kwargs: Any) -> Markup:
        kwargs.setdefault('class', 'form-label')
        if self.description:
            kwargs.setdefault('title', self.description)
            kwargs.setdefault('data_bs_toggle', 'tooltip')
        return super().__call__(text=text, **kwargs)


class Form(BaseForm):

    Meta = BootstrapMeta

    def process(
        self,
        formdata:      '_MultiDictLike | None' = None,
        obj:           object | None = None,
        data:          'Mapping[str, Any] | None' = None,
        extra_filters: 'Mapping[str, Sequence[Any]] | None' = None,
        **kwargs: Any
    ) -> None:

        formdata = self.meta.wrap_formdata(self, formdata)

        if data is not None:
            kwargs = dict(data, **kwargs)

        for name, field, in self._fields.items():
            if isinstance(field, TransparentFormField):
                # NOTE: Treat the subform transparently with no prefix
                #       and the same object/field access
                field.form = field.form_class(
                    formdata=formdata,
                    obj=obj,
                    data=data,
                    **kwargs
                )
            elif obj is not None and hasattr(obj, name):
                field.process(formdata, getattr(obj, name))
            elif name in kwargs:
                field.process(formdata, kwargs[name])
            else:
                field.process(formdata)
