from sqlalchemy import JSON
from sqlalchemy import TypeDecorator
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.types import TypeEngine
from sqlalchemy.dialects.postgresql import JSONB


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect


class JSONObject(TypeDecorator[dict[str, Any]]):
    """
    Stores arbitrary JSON objects.

    Uses JSONB on Postgres for the most efficient storage backend.
    """

    impl = TypeEngine

    def load_dialect_impl(self, dialect: 'Dialect') -> TypeEngine[Any]:
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB(none_as_null=True))
        return dialect.type_descriptor(JSON(none_as_null=True))


# NOTE: MutableDict doesn't track nested mutations, we could accomplish
#       this by overriding MutableDict and MutableList with type coercion
#       to MutableDict/MutableList when setting dict/list values and do
#       so recursively. But it's probably not worth the overhead.
MutableDict.associate_with(JSONObject)
