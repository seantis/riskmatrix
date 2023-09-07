from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from pyramid.httpexceptions import HTTPFound
    from pyramid.interfaces import IRequest
    from pyramid.interfaces import IResponse

    from typing import Any
    from typing import Literal
    from typing import Protocol
    from typing import TypeVar
    from typing_extensions import TypeAlias

    _Tco = TypeVar('_Tco', covariant=True)

    JSON: TypeAlias = (
        dict[str, 'JSON'] | list['JSON']
        | str | int | float | bool | None
    )
    JSONObject: TypeAlias = dict[str, JSON]
    JSONArray: TypeAlias = list[JSON]

    # read only variant of JSON type that is covariant
    JSON_ro: TypeAlias = (
        Mapping[str, 'JSON_ro'] | Sequence['JSON_ro']
        | str | int | float | bool | None
    )
    JSONObject_ro: TypeAlias = Mapping[str, JSON_ro]
    JSONArray_ro: TypeAlias = Sequence[JSON_ro]

    ACL: TypeAlias = tuple[Literal['Allow', 'Deny'], str, list[str]]

    RenderData: TypeAlias = dict[str, Any]
    RenderDataOrRedirect: TypeAlias = RenderData | HTTPFound
    RenderDataOrResponse: TypeAlias = RenderData | IResponse

    # NOTE: For now we only allow complex return types if we return JSON
    #       If you want to return a scalar type as JSON you need to be
    #       explicit about it.
    XHRData: TypeAlias = JSONObject_ro | JSONArray_ro
    XHRDataOrRedirect: TypeAlias = XHRData | HTTPFound
    XHRDataOrResponse: TypeAlias = XHRData | IResponse

    MixedData: TypeAlias = RenderData | XHRData
    MixedDataOrRedirect: TypeAlias = MixedData | HTTPFound
    MixedDataOrResponse: TypeAlias = MixedData | IResponse

    class Callback(Protocol[_Tco]):
        def __call__(self, context: Any, request: IRequest) -> _Tco: ...

    CallbackOrValue: TypeAlias = Callback[_Tco] | _Tco
