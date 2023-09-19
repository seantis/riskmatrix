from datetime import datetime
from pyramid.authorization import Allow
from sedate import utcnow
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates
from sqlalchemy.orm import Mapped
from uuid import uuid4

from riskmatrix.models import Asset
from riskmatrix.models import Risk
from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK


from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.types import ACL


class RiskAssessment(Base):

    __tablename__ = 'risk_assessment'
    __table_args__ = (
        UniqueConstraint('risk_id', 'asset_id'),
    )

    id: Mapped[UUIDStrPK]
    asset_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('asset.id', ondelete='CASCADE'),
        index=True,
    )
    risk_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('risk.id', ondelete='CASCADE'),
        index=True,
    )

    meta: Mapped[dict[str, Any]] = mapped_column(default={})
    impact: Mapped[int | None]
    likelihood: Mapped[int | None]

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    risk: Mapped[Risk] = relationship(
        back_populates='assessments',
        lazy='joined'
    )
    asset: Mapped[Asset] = relationship(
        back_populates='assessments',
        lazy='joined'
    )

    def __init__(
        self,
        asset:  Asset,
        risk:   Risk,
        **meta: Any
    ):
        self.id = str(uuid4())
        self.created = utcnow()
        self.asset = asset
        self.risk = risk
        self.meta = meta

    @validates('impact', 'likelihood')
    def ensure_larger_than_one(
        self,
        key:       str,
        magnitude: int | None
    ) -> int | None:

        if magnitude is None:
            return None

        if magnitude < 1:
            raise ValueError(f'{key} cannot be lower than 1')

        return magnitude

    @validates('risk')
    def ensure_consistent_organization(
        self,
        key:  str,
        risk: Risk
    ) -> Risk:

        if self.asset.organization_id != risk.organization_id:
            raise ValueError(
                'Inconsistent organization between risk and asset'
            )

        return risk

    @hybrid_property
    def name(self) -> str:
        return self.risk.name

    @name.inplace.expression
    @classmethod
    def _name_expression(cls) -> Mapped[str]:
        return Risk.name

    @hybrid_property
    def description(self) -> str | None:
        return self.risk.description

    @description.inplace.expression
    @classmethod
    def _description_expression(cls) -> Mapped[str | None]:
        return Risk.description

    @hybrid_property
    def category(self) -> str | None:
        return self.risk.category

    @category.inplace.expression
    @classmethod
    def _category_expression(cls) -> Mapped[str | None]:
        return Risk.category

    @hybrid_property
    def asset_name(self) -> str:
        return self.asset.name

    @asset_name.inplace.expression
    @classmethod
    def _asset_name_expression(cls) -> Mapped[str]:
        return Asset.name

    @hybrid_property
    def organization_id(self) -> str:
        return self.risk.organization_id

    @organization_id.inplace.expression
    @classmethod
    def _organization_id_expression(cls) -> Mapped[str]:
        return Risk.organization_id

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, f'org_{self.risk.organization_id}', ['view']),
        ]
