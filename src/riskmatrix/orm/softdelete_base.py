from sqlalchemy_easy_softdelete.mixin import generate_soft_delete_mixin_class  # type: ignore

from sqlalchemy.sql import func

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class SoftDeleteMixin(generate_soft_delete_mixin_class( # type: ignore[misc]
    ignored_tables=[]
)):
    deleted_at: 'datetime'

    def soft_delete(self) -> None:
        self.deleted_at = func.now()
