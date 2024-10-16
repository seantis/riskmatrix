from datetime import datetime
from pyramid.authorization import Allow
from sedate import utcnow
from riskmatrix.orm.softdelete_base import SoftDeleteMixin
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates
from sqlalchemy.orm import Mapped
from uuid import uuid4

from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import str_128
from riskmatrix.orm.meta import Text
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK

from sqlalchemy_serializer import SerializerMixin

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.models import Organization
    from riskmatrix.models import Risk
    from riskmatrix.types import ACL


class RiskCatalog(Base, SoftDeleteMixin, SerializerMixin):

    __tablename__ = 'risk_catalog'
    __table_args__ = (
        UniqueConstraint('organization_id', 'name'),
    )

    id: Mapped[UUIDStrPK] = mapped_column()
    organization_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE'),
        index=True,
    )
    name: Mapped[str_128]
    description: Mapped[Text | None]

    parent_id: Mapped[UUIDStr | None] = mapped_column(
        ForeignKey('risk_catalog.id', ondelete='CASCADE'),
        index=True,
    )
    children: Mapped[list['RiskCatalog']] = relationship(
        back_populates='parent',
        cascade='all, delete-orphan',
        viewonly=True
    )
    parent: Mapped['RiskCatalog | None'] = relationship(
        back_populates='children',
        remote_side=id
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    risks: Mapped[list['Risk']] = relationship(back_populates='catalog')
    organization: Mapped['Organization'] = relationship(back_populates='risk_catalogs')

    def __init__(
        self,
        name:         str,
        organization: 'Organization',
        description:  str | None = None,
        parent:       'RiskCatalog | None' = None,
    ):
        self.id = str(uuid4())
        self.created = utcnow()
        self.name = name
        self.description = description
        self.organization = organization
        self.parent = parent

    @validates('parent')
    def ensure_consistent_organization(
        self,
        key: str,
        parent: 'RiskCatalog | None'
    ) -> 'RiskCatalog | None':

        if parent is not None and parent.organization != self.organization:
            raise ValueError(
                'parent catalog is assigned to a different organization'
            )

        return parent

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, f'org_{self.organization_id}', ['view']),
        ]
