from datetime import datetime
from pyramid.authorization import Allow
from sedate import utcnow
from riskmatrix.orm.softdelete_base import SoftDeleteMixin
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from uuid import uuid4

from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import str_256
from riskmatrix.orm.meta import Text
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.sql import ColumnElement

    from riskmatrix.models import Organization
    from riskmatrix.models import RiskAssessment
    from riskmatrix.types import ACL

from sqlalchemy_serializer import SerializerMixin


class Asset(Base, SoftDeleteMixin, SerializerMixin):

    __tablename__ = 'asset'
    __table_args__ = (
        UniqueConstraint('organization_id', 'name'),
    )

    id: Mapped[UUIDStrPK]
    organization_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE'),
        index=True,
    )
    name: Mapped[str_256] = mapped_column(index=True)
    description: Mapped[Text | None]
    meta: Mapped[dict[str, Any]] = mapped_column(default={})

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    assessments: Mapped[list['RiskAssessment']] = relationship(
        back_populates='asset'
    )

    organization: Mapped['Organization'] = relationship(
        back_populates='assets'
    )

    def __init__(
        self,
        name:         str,
        organization: 'Organization',
        description:  str | None = None,
        **meta:       Any
    ):
        self.id = str(uuid4())
        self.created = utcnow()
        self.name = name
        self.description = description
        self.organization = organization
        self.meta = meta

    @hybrid_property
    def catalog_ids(self) -> list[str]:
        return self.meta.get('catalogs', [])

    @catalog_ids.inplace.setter
    def _catalog_ids_setter(self, value: list[str]) -> None:
        self.meta['catalogs'] = value

    @catalog_ids.inplace.expression
    @classmethod
    def _catalog_ids_expression(cls) -> 'ColumnElement[list[str]]':
        return cls.meta['catalogs']

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, f'org_{self.organization_id}', ['view']),
        ]
