from sqlalchemy_easy_softdelete.mixin import generate_soft_delete_mixin_class
from sqlalchemy_easy_softdelete.hook import IgnoredTable
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer
from datetime import datetime
from sqlalchemy.sql import func

# Create a Class that inherits from our class builder
class SoftDeleteMixin(generate_soft_delete_mixin_class(
    # This table will be ignored by the hook
    # even if the table has the soft-delete column
    ignored_tables=[]
)):
    # type hint for autocomplete IDE support
    deleted_at: datetime

    def soft_delete(self):
        self.deleted_at = func.now()