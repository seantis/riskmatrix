import translationstring
from functools import update_wrapper
from markupsafe import escape
from markupsafe import Markup

from .core import translate


from typing import overload
from typing import Any
from typing import Literal
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from markupsafe import HasHTML
    from typing import Protocol
    from typing_extensions import Self

    class TStrCallable(Protocol):
        @overload
        def __call__(
            self,
            msgid: HasHTML,
            mapping: dict[str, Any] | None = None,
            default: str | HasHTML | None = None,
            context: str | None = None,
            *,
            markup: bool = False,
        ) -> 'TranslationMarkup': ...

        @overload
        def __call__(
            self,
            msgid: str | HasHTML,
            mapping: dict[str, Any] | None = None,
            default: str | HasHTML | None = None,
            context: str | None = None,
            *,
            markup: Literal[True],
        ) -> 'TranslationMarkup': ...

        @overload
        def __call__(
            self,
            msgid: str,
            mapping: dict[str, Any] | None = None,
            default: str | None = None,
            context: str | None = None,
            *,
            markup: bool = False,
        ) -> 'TranslationString': ...


class TranslationString(translationstring.TranslationString):
    """
    TranslationString that will eagerly translate when used
    inside a Markup.format()
    """

    def __mod__(self, options: Any) -> 'Self':
        return type(self)(super().__mod__(options))

    def translated(self, language: str | None = None) -> str:
        return translate(self, language)

    def __html__(self) -> Markup:
        return escape(self.translated())

    # NOTE: Allow specifying language in format string
    #       e.g. '{:de}'.format(_(Markup('<b>Bold</b>')))
    def __html_format__(self, format_spec: str) -> Markup:
        if format_spec:
            return escape(self.translated(format_spec))
        return self.__html__()


class TranslationMarkup(TranslationString):
    """
    Markup aware version of TranslationString
    """
    __slots__ = ('domain', 'context', 'default', 'mapping')

    domain: str | None
    context: str | None
    default: Markup
    mapping: dict[str, Markup] | None

    def __new__(
        cls,
        msgid: 'str | HasHTML | Self',
        domain: str | None = None,
        default: 'str | HasHTML | None' = None,
        mapping: dict[str, Any] | None = None,
        context: str | None = None,
    ) -> 'Self':

        _default: Markup | None
        if default is None:
            _default = None
        else:
            _default = Markup(default)  # noqa: MS001

        # NOTE: We prepare everything in the mapping with escape
        #       because interpolate uses re.sub, which is not
        #       Markup aware and thus will not escape params.
        _mapping: dict[str, Markup] | None
        if mapping is None:
            _mapping = None
        else:
            _mapping = {k: escape(v) for k, v in mapping.items()}

        if not isinstance(msgid, str) and hasattr(msgid, '__html__'):
            msgid = Markup(msgid)  # noqa: MS001

        elif isinstance(msgid, translationstring.TranslationString):
            domain = domain or msgid.domain and msgid.domain[:]
            context = context or msgid.context and msgid.context[:]
            _default = _default or Markup(msgid.default)  # noqa: MS001
            if msgid.mapping:
                if _mapping:
                    for k, v in msgid.mapping.items():
                        _mapping.setdefault(k, escape(v))
                else:
                    _mapping = {k: escape(v) for k, v in msgid.mapping.items()}
            msgid = Markup(str(msgid))  # noqa: MS001

        instance: 'Self' = str.__new__(cls, msgid)
        instance.domain = domain
        instance.context = context
        if _default is None:
            _default = Markup(msgid)  # noqa: MS001
        instance.default = _default

        instance.mapping = _mapping
        return instance

    def __mod__(self, options: Any) -> 'Self':
        if isinstance(options, dict):
            # Ensure everything is escaped before it gets replaced
            options = {k: escape(v) for k, v in options.items()}
        return type(self)(super().__mod__(options))

    def interpolate(self, translated: str | None = None) -> Markup:
        if translated is not None:
            translated = Markup(translated)  # noqa: MS001
        return Markup(super().interpolate(translated))  # noqa: MS001

    @classmethod
    def escape(cls, s: Any) -> 'Self':
        if isinstance(s, cls):
            return s
        elif isinstance(s, TranslationString):
            return cls(
                escape(s),
                domain=s.domain and s.domain[:],
                default=s.default and escape(s.default),
                mapping=s.mapping,
                context=s.context and s.context[:],
            )
        return cls(escape(s))

    def translated(self, language: str | None = None) -> Markup:
        return Markup(translate(self, language))  # noqa: MS001


def TranslationStringFactory(factory_domain: str) -> 'TStrCallable':
    """
    Creates a TranslationMarkup for Markup and a TranslationString
    otherwise.
    """
    @overload
    def create(
        msgid: 'HasHTML',
        mapping: dict[str, Any] | None = None,
        default: 'str | HasHTML | None' = None,
        context: str | None = None,
        *,
        markup: bool = False,
    ) -> TranslationMarkup: ...
    @overload  # noqa: E306
    def create(
        msgid: 'str | HasHTML',
        mapping: dict[str, Any] | None = None,
        default: 'str | HasHTML | None' = None,
        context: str | None = None,
        *,
        markup: Literal[True],
    ) -> TranslationMarkup: ...
    @overload  # noqa: E306
    def create(
        msgid: 'str',
        mapping: dict[str, Any] | None = None,
        default: 'str | None' = None,
        context: str | None = None,
        *,
        markup: bool = False,
    ) -> TranslationString: ...

    def create(
        msgid: 'str | HasHTML',
        mapping: dict[str, Any] | None = None,
        default: 'str | HasHTML | None' = None,
        context: str | None = None,
        *,
        markup: bool = False,
    ) -> TranslationString:

        klass: type[TranslationString]
        if markup or hasattr(msgid, '__html__'):
            klass = TranslationMarkup
        elif hasattr(default, '__html__'):
            raise ValueError(
                'Markup default value not allowed without '
                'Markup msgid.'
            )
        else:
            klass = TranslationString

        if isinstance(msgid, TranslationString):
            domain = msgid.domain or factory_domain
        else:
            domain = factory_domain

        return klass(
            msgid,  # type:ignore[arg-type]
            domain=domain,
            default=default,  # type:ignore[arg-type]
            mapping=mapping,
            context=context
        )
    return create


# monkeypatch translationstring.dugettext_policy to preserve Markup
# TODO: Also monkeypatch dungettext_policy for pluralizer?
_orig_dugettext_policy = translationstring.dugettext_policy


def _dugettext_policy(
    translations: Any,
    tstring:      str,
    domain:       str | None,
    context:      str | None
) -> str:

    translated = _orig_dugettext_policy(translations, tstring, domain, context)
    if (
        hasattr(tstring, '__html__')
        and not hasattr(translated, '__html__')
        # our plain TranslationString also implements __html__ but
        # we don't want it to get interpolated into Markup
        and not type(tstring) is TranslationString
    ):
        return Markup(translated)  # noqa: MS001
    return translated


update_wrapper(_dugettext_policy, _orig_dugettext_policy)
translationstring.dugettext_policy = _dugettext_policy
