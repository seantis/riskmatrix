from datetime import datetime
from pyramid.authorization import Allow
from sedate import utcnow
from riskmatrix.orm.softdelete_base import SoftDeleteMixin
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from uuid import uuid4

from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import str_128
from riskmatrix.orm.meta import str_256
from riskmatrix.orm.meta import Text
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.models import Organization
    from riskmatrix.models import RiskAssessment
    from riskmatrix.models import RiskCatalog
    from riskmatrix.types import ACL

from sqlalchemy_serializer import SerializerMixin

class Risk(SoftDeleteMixin, Base, SerializerMixin):

    __tablename__ = 'risk'
    __table_args__ = (
        UniqueConstraint('organization_id', 'name'),
        ForeignKeyConstraint(
            ['category', 'organization_id'],
            ['risk_category.name', 'risk_category.organization_id'],
            onupdate='CASCADE'
        ),
    )

    id: Mapped[UUIDStrPK]
    organization_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE'),
        index=True,
    )
    name: Mapped[str_256] = mapped_column(index=True)
    description: Mapped[Text | None]
    category: Mapped[str_128 | None] = mapped_column(index=True)
    catalog_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('risk_catalog.id', ondelete='CASCADE'),
        index=True,
    )
    meta: Mapped[dict[str, Any]] = mapped_column(default={})

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    assessments: Mapped[list['RiskAssessment']] = relationship(
        back_populates='risk'
    )
    catalog: Mapped['RiskCatalog'] = relationship(back_populates='risks')
    organization: Mapped['Organization'] = relationship(back_populates='risks')

    def __init__(
        self,
        name:        str,
        catalog:     'RiskCatalog',
        description: str | None = None,
        category:    str | None = None,
        **meta:      Any
    ):
        self.id = str(uuid4())
        self.created = utcnow()
        self.name = name
        self.description = description
        self.catalog = catalog
        self.organization_id = catalog.organization_id
        self.category = category
        self.meta = meta

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, f'org_{self.organization_id}', ['view']),
        ]
