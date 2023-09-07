from markupsafe import escape
from markupsafe import Markup
from translationstring import TranslationString

from .util import translate


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
        ) -> TranslationString: ...


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
            _default = Markup(default)

        # NOTE: We prepare everything in the mapping with escape
        #       because interpolate uses re.sub, which is not
        #       Markup aware and thus will not escape params.
        _mapping: dict[str, Markup] | None
        if mapping is None:
            _mapping = None
        else:
            _mapping = {k: escape(v) for k, v in mapping.items()}

        if not isinstance(msgid, str) and hasattr(msgid, '__html__'):
            msgid = Markup(msgid)

        elif isinstance(msgid, TranslationString):
            domain = domain or msgid.domain and msgid.domain[:]
            context = context or msgid.context and msgid.context[:]
            _default = _default or Markup(msgid.default)
            if msgid.mapping:
                if _mapping:
                    for k, v in msgid.mapping.items():
                        _mapping.setdefault(k, escape(v))
                else:
                    _mapping = {k: escape(v) for k, v in msgid.mapping.items()}
            msgid = Markup(msgid)

        instance: 'Self' = str.__new__(cls, msgid)
        instance.domain = domain
        instance.context = context
        if _default is None:
            _default = Markup(msgid)
        instance.default = _default

        instance.mapping = _mapping
        return instance

    def __mod__(self, options: Any) -> 'Self':
        if isinstance(options, dict):
            # Ensure everything is escaped before it gets replaced
            options = {k: escape(v) for k, v in options.items()}
        return type(self)(super().__mod__(options))

    def interpolate(self, translated: str | None = None) -> Markup:
        return Markup(super().interpolate(translated and Markup(translated)))

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

    def __html__(self) -> Markup:
        return Markup(translate(self))

    # NOTE: Allow specifying language in format string
    #       e.g. '{:de}'.format(_(Markup('<b>Bold</b>')))
    def __html_format__(self, format_spec: str) -> Markup:
        if format_spec:
            return Markup(translate(self, format_spec))
        return self.__html__()


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
