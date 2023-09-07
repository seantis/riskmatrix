from markupsafe import Markup
from pyramid.i18n import TranslationString

from riskmatrix.i18n.translation_string import TranslationMarkup


def test_init():
    markup = TranslationMarkup('<b>bold</b>')
    assert str(markup) == '<b>bold</b>'
    assert isinstance(markup.interpolate(), Markup)
    assert markup.interpolate() == Markup('<b>bold</b>')
    assert Markup(markup) == Markup('<b>bold</b>')
    assert markup.domain is None
    assert markup.mapping is None
    assert markup.context is None
    assert isinstance(markup.default, Markup)
    assert markup.default == Markup(markup)


def test_init_mapping_plain():
    markup = TranslationMarkup(
        '<b>${arg}</b>',
        mapping={'arg': '<i>unsafe</i>'}
    )
    assert markup.mapping == {'arg': Markup('&lt;i&gt;unsafe&lt;/i&gt;')}
    assert markup.interpolate() == Markup('<b>&lt;i&gt;unsafe&lt;/i&gt;</b>')


def test_init_mapping_markup():
    markup = TranslationMarkup(
        '<b>${arg}</b>',
        mapping={'arg': Markup('<i>italic</i>')}
    )
    assert markup.mapping == {'arg': Markup('<i>italic</i>')}
    assert markup.interpolate() == Markup('<b><i>italic</i></b>')


def test_init_translation_string():
    plain = TranslationString(
        '<b>${arg}</b>',
        mapping={'arg': '<i>unsafe</i>'},
        domain='riskmatrix',
        default='<u>${arg}</u>',
        context='context',
    )
    markup = TranslationMarkup(plain)
    assert str(markup) == '<b>${arg}</b>'
    assert markup.domain == 'riskmatrix'
    assert isinstance(markup.default, Markup)
    assert markup.default == Markup('<u>${arg}</u>')
    assert markup.mapping == {'arg': Markup('&lt;i&gt;unsafe&lt;/i&gt;')}
    assert markup.interpolate() == Markup('<u>&lt;i&gt;unsafe&lt;/i&gt;</u>')


def test_escape():
    unsafe = TranslationString('<b>unsafe</b>', domain='riskmatrix')
    escaped = TranslationMarkup.escape(unsafe)
    assert escaped.domain == 'riskmatrix'
    assert str(escaped) == '&lt;b&gt;unsafe&lt;/b&gt;'
    assert escaped.interpolate() == Markup('&lt;b&gt;unsafe&lt;/b&gt;')


def test_mod_markup():
    markup = TranslationMarkup('<b>${arg}</b>')
    updated = markup % {'arg': Markup('<i>italic</i>')}
    assert updated.mapping == {'arg': Markup('<i>italic</i>')}
    assert updated.interpolate() == Markup('<b><i>italic</i></b>')


def test_mod_plain():
    markup = TranslationMarkup('<b>${arg}</b>')
    updated = markup % {'arg': '<i>unsafe</i>'}
    assert updated.mapping == {'arg': Markup('&lt;i&gt;unsafe&lt;/i&gt;')}
    assert updated.interpolate() == Markup('<b>&lt;i&gt;unsafe&lt;/i&gt;</b>')


def test_interpolate():
    markup = TranslationMarkup('<b>bold</b>')
    assert markup.interpolate() == Markup('<b>bold</b>')
    assert markup.interpolate('<b>fett</b>') == Markup('<b>fett</b>')


def test_html():
    markup = TranslationMarkup('<b>bold</b>')
    assert markup.__html__() == Markup('<b>bold</b>')


def test_html_format(config):
    config.add_translation_dirs('riskmatrix:locale/')
    # Testing localizer doesn't seem to work.
    config.registry.localizer_de = None
    msg = TranslationMarkup('Just a test', domain='riskmatrix')
    assert Markup('{}').format(msg) == Markup('Just a test')
    assert Markup('{:en}').format(msg) == Markup('Just a test')
    assert Markup('{:de}').format(msg) == Markup('Nur ein Test')
