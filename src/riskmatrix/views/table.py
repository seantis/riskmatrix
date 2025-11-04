from markupsafe import Markup
from riskmatrix.i18n import _

from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


class Button:
    def __init__(
        self,
        url: str,
        icon: str,
        title: str,
        css_class: str = '',
        modal: str | None = None,
        data_table_id: str | None = None,
    ):
        self.url = url
        self.icon = icon
        self.title = title
        self.css_class = css_class
        self.modal = modal
        self.data_table_id = data_table_id

    def __html__(self) -> str:
        attrs = {
            'href': self.url,
            'class': f'btn {self.css_class}',
            'title': self.title,
        }
        if self.modal:
            attrs['data-bs-toggle'] = 'modal'
            attrs['data-bs-target'] = self.modal
        if self.data_table_id:
            attrs['data-table-id'] = self.data_table_id

        attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<a {attrs_str}><i class="fa fa-{self.icon}"></i> {self.title}</a>'


class Column:
    def __init__(
        self,
        label: str,
        sortable: bool = False,
        searchable: bool = True,
        width: str | None = None,
    ):
        self.label = label
        self.sortable = sortable
        self.searchable = searchable
        self.width = width


class Table:
    def __init__(self, request: 'IRequest'):
        self.request = request
        self.id = self.__class__.__name__.lower()

    def query(self) -> Any:
        raise NotImplementedError()

    def __html__(self) -> str:
        columns = []
        for name, attr in self.__class__.__dict__.items():
            if isinstance(attr, Column):
                columns.append((name, attr))

        headers = ''.join(f'<th>{col.label}</th>' for _, col in columns)
        table = f'''
        <table id="{self.id}" class="table table-striped">
            <thead>
                <tr>{headers}</tr>
            </thead>
        </table>
        '''
        return Markup(table)  # noqa: S308 