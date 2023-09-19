from .core import pluralize
from .core import translate
from .locale_negotiator import LocaleNegotiator
from .translation_string import TranslationStringFactory


_ = TranslationStringFactory('riskmatrix')

__all__ = (
    '_',
    'LocaleNegotiator',
    'pluralize',
    'translate'
)
