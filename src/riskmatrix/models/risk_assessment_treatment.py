from datetime import datetime
from sedate import utcnow
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.types import JSON
from uuid import uuid4
import enum

from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import Text
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK
from sqlalchemy_serializer import SerializerMixin

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.models import RiskAssessment


class TreatmentType(enum.Enum):
    REDUCE = "Reduce"
    ACCEPT = "Accept"
    AVOID = "Avoid"
    TRANSFER = "Transfer/Share"

    def __str__(self) -> str:
        return self.value


class RiskAssessmentTreatment(Base, SerializerMixin):
    __tablename__ = 'risk_assessment_treatment'

    id: Mapped[UUIDStrPK]
    risk_assessment_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('risk_assessment.id', ondelete='CASCADE'),
        index=True,
    )
    description: Mapped[Text | None]
    links: Mapped[list[str]] = mapped_column(JSON, default=list)
    treatment_type: Mapped[TreatmentType] = mapped_column(
        Enum(TreatmentType),
        default=TreatmentType.REDUCE,
    )
    post_likelihood: Mapped[int | None]
    post_impact: Mapped[int | None]

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    risk_assessment: Mapped['RiskAssessment'] = relationship(
        back_populates='treatment',
        lazy='joined'
    )

    def __init__(
        self,
        risk_assessment: 'RiskAssessment',
        description: str | None = None,
        links: list[str] | None = None,
        treatment_type: TreatmentType = TreatmentType.REDUCE,
        post_likelihood: int | None = None,
        post_impact: int | None = None
    ):
        self.id = str(uuid4())
        self.created = utcnow()
        self.risk_assessment = risk_assessment
        self.description = description
        self.links = links or []
        self.treatment_type = treatment_type
        self.post_likelihood = post_likelihood
        self.post_impact = post_impact 