from babel import Locale
from wtforms import RadioField
from wtforms import StringField
from wtforms import validators
from pyramid.httpexceptions import HTTPFound

from riskmatrix.i18n import _
from riskmatrix.wtform import Form


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from ..models import Organization
    from ..types import RenderDataOrRedirect


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
        return {'errors': form.errors}
    else:
        return {
            'title': 'Organization',
            'form': form,
            'target_url': target_url,
            'csrf_token': request.session.get_csrf_token(),
        }
