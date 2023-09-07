from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest

    from riskmatrix.types import RenderData


def flash(context: object, request: 'IRequest') -> 'RenderData':
    messages = request.messages.pop()
    if not messages:
        return {}

    return {
        'messages': messages
    }
