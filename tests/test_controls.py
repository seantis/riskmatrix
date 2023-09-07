import pytest

from riskmatrix.controls import Button
from riskmatrix.controls import Icon


def test_icon():
    icon = Icon('plus')
    assert icon() == '<i class="far fa-plus"></i>'


def test_icon_style():
    icon = Icon('plus', style=Icon.Style.regular)
    assert icon.style == Icon.Style.regular
    assert icon() == '<i class="far fa-plus"></i>'

    icon = Icon('plus', style=Icon.Style.solid)
    assert icon.style == Icon.Style.solid
    assert icon() == '<i class="fas fa-plus"></i>'

    icon = Icon('plus', style=Icon.Style.light)
    assert icon.style == Icon.Style.light
    assert icon() == '<i class="fal fa-plus"></i>'

    icon = Icon('plus', style=Icon.Style.duotone)
    assert icon.style == Icon.Style.duotone
    assert icon() == '<i class="fad fa-plus"></i>'


def test_icon_str():
    icon = Icon('plus')
    assert str(icon) == '<i class="far fa-plus"></i>'


def test_icon_html():
    icon = Icon('plus')
    assert icon.__html__() == '<i class="far fa-plus"></i>'


def test_button():
    button = Button()
    assert button() == '<button class="btn" type="button"></button>'


def test_button_name():
    button = Button('edit')
    assert button() == (
        '<button class="btn" name="edit" type="button"></button>'
    )

    button = Button('edit', url='#')
    assert button() == '<a class="btn" href="#" id="edit" role="button"></a>'


def test_button_title():
    button = Button(title='Edit')
    assert button() == '<button class="btn" type="button">Edit</button>'


def test_button_description():
    button = Button(description='Edit')
    assert button() == (
        '<button class="btn" type="button">'
        '<span title="Edit" data-bs-toggle="tooltip"></span>'
        '</button>'
    )


def test_button_url():
    button = Button(url='http://example.com')
    assert button() == (
        '<a class="btn" href="http://example.com" role="button"></a>'
    )


def test_button_submit():
    with pytest.raises(ValueError, match=r'Submit button requires "name"\.'):
        Button(submit=True)

    button = Button('save', submit=True)
    assert button.name == 'save'
    assert button() == (
        '<button class="btn" name="save" type="submit" value="save"></button>'
    )


def test_button_icon():
    button = Button(icon='plus')
    assert button() == (
        '<button class="btn" type="button">'
        '<i class="far fa-plus"></i>'
        '</button>'
    )

    button = Button(icon=Icon('plus', style=Icon.Style.solid))
    assert button() == (
        '<button class="btn" type="button">'
        '<i class="fas fa-plus"></i>'
        '</button>'
    )


def test_button_modal():
    button = Button(modal='#confirm')
    assert button() == (
        '<button class="btn" data-bs-target="#confirm" data-bs-toggle="modal" '
        'type="button"></button>'
    )


def test_button_css_class():
    button = Button(css_class='btn-primary')
    assert button() == (
        '<button class="btn btn-primary" type="button"></button>'
    )


def test_button_remove_button():
    button = Button(remove_button=True)
    assert button() == (
        '<button class="btn remove-button" type="button"></button>'
    )


def test_button_remove_row():
    button = Button(remove_row=True)
    assert button() == (
        '<button class="btn remove-row" type="button"></button>'
    )


def test_button_remove_button_and_row():
    with pytest.raises(
        ValueError, match=r'Can\'t remove both the button and the row\.'
    ):
        Button(remove_button=True, remove_row=True)


def test_button_str():
    button = Button()
    assert str(button) == '<button class="btn" type="button"></button>'


def test_button_html():
    button = Button()
    assert button.__html__() == '<button class="btn" type="button"></button>'


def test_button_complex():
    button = Button('edit', title='Edit', icon='edit', description='Edit Item')
    assert button() == (
        '<button class="btn" name="edit" type="button">'
        '<span title="Edit Item" data-bs-toggle="tooltip">'
        '<i class="far fa-edit"></i> Edit'
        '</span>'
        '</button>'
    )
