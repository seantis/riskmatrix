from enum import Enum
from markupsafe import Markup
from wtforms.widgets import html_params

from riskmatrix.i18n import translate


from typing import ClassVar
from typing import Literal


class IconStyle(Enum):
    regular = 'far'
    solid = 'fas'
    light = 'fal'
    duotone = 'fad'

    def __str__(self) -> str:
        return self.value


class Icon:
    # allow IconStyle access via Icon.Style
    Style: ClassVar[type[IconStyle]] = IconStyle

    def __init__(self, name: str, style: IconStyle = IconStyle.regular):
        self.name = name
        self.style = style

    def __call__(self) -> Markup:
        return Markup('<i class="{} fa-{}"></i>').format(self.style, self.name)

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()


class Button:
    element:       Literal['a', 'button']
    name:          str
    title:         str
    description:   str
    url:           str
    submit:        bool
    value:         str | None
    icon:          Icon | None
    modal:         str | None
    disabled:      bool
    remove_button: bool
    remove_row:    bool
    html_params:   dict[str, str | bool | None]

    def __init__(
        self,
        name:  str = '',
        title: str = '',
        *,
        description:   str = '',
        url:           str = '',
        submit:        bool = False,
        value:         str | None = None,
        icon:          str | Icon | None = None,
        modal:         str | None = None,
        css_class:     str | None = None,
        disabled:      bool = False,
        remove_button: bool = False,
        remove_row:    bool = False,
        **html_params: str | bool | None
    ):
        self.name = name
        self.title = title
        self.description = description
        self.url = url
        self.submit = submit
        self.value = value
        self.disabled = disabled

        if isinstance(icon, Icon):
            self.icon = icon
        elif isinstance(icon, str):
            self.icon = Icon(icon)
        else:
            self.icon = None

        self.modal = modal
        if remove_button and remove_row:
            raise ValueError('Can\'t remove both the button and the row.')

        self.remove_button = remove_button
        self.remove_row = remove_row

        self.html_params = html_params
        if css_class:
            css_class = 'btn ' + css_class
        else:
            css_class = 'btn'
        if self.remove_row:
            css_class += ' remove-row'
        elif self.remove_button:
            css_class += ' remove-button'

        if self.disabled:
            self.html_params['disabled'] = 'disabled'
            css_class += ' disabled'
        elif self.modal:
            self.html_params['data-bs-toggle'] = 'modal'
            self.html_params['data-bs-target'] = self.modal

        self.html_params['class'] = css_class

        if self.submit:
            if not name:
                raise ValueError('Submit button requires "name".')
            self.element = 'button'
            self.html_params['name'] = name
            self.html_params['type'] = 'submit'
            self.html_params['value'] = self.value if self.value else name
        elif self.url:
            self.element = 'a'
            self.html_params['href'] = self.url
            self.html_params['role'] = 'button'
            if name:
                self.html_params['id'] = name
        else:
            self.element = 'button'
            self.html_params['type'] = 'button'
            if name:
                self.html_params['name'] = name

    def __call__(self) -> Markup:
        assert self.element in ('a', 'button')
        if self.disabled and self.description:
            desc_params = {
                'title': translate(self.description),
                'class': 'd-inline-block',
                'tabindex': 0,
                'data_bs_toggle': 'tooltip'
            }
            html = Markup(f'<span {html_params(**desc_params)}>')
        else:
            html = Markup('')

        html += Markup(f'<{self.element} {html_params(**self.html_params)}>')

        if not self.disabled and self.description:
            description = html_params(title=translate(self.description))
            html += Markup(f'<span {description} data-bs-toggle="tooltip">')

        if self.icon:
            html += self.icon()
        if self.icon and self.title:
            html += ' '

        html += translate(self.title)

        if not self.disabled and self.description:
            html += Markup('</span>')

        html += Markup(f'</{self.element}>')

        if self.disabled and self.description:
            html += Markup('</span>')

        return html

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()
