from dataclasses import dataclass
from sedate import utcnow
from riskmatrix.orm.meta import Base
import enum
from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK
from sqlalchemy import UniqueConstraint
from sqlalchemy import Column
from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from riskmatrix.models import RiskAssessment
    



class RiskAssessmentState(enum.Enum):
    OPEN = 0
    FINISHED = 1

    def __str__(self) -> str:
        names = {
            RiskAssessmentState.OPEN: "Offen",
            RiskAssessmentState.FINISHED: "Geschlossen"
        }
        return names[self]

from sqlalchemy_serializer import SerializerMixin


class RiskAssessmentInfo(Base, SerializerMixin):

    __tablename__ = 'risk_assessment_info'

    id: Mapped[UUIDStrPK] = mapped_column()
    organization_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE'),
        index=True,
    )
    
    name: Mapped[str] = mapped_column(nullable=True)

    state: Mapped[RiskAssessmentState] = mapped_column(
        Enum(RiskAssessmentState),
        default=RiskAssessmentState.OPEN,
    )

    created: Mapped[datetime] = mapped_column(default=utcnow)
    modified: Mapped[datetime | None] = mapped_column(onupdate=utcnow)

    finished_at: Mapped[datetime | None] = mapped_column()

    assessments: Mapped[list['RiskAssessment']] = relationship(
        back_populates='risk_assessment_info'
    )

    def __init__(self, organization_id: str):
        self.organization_id = organization_id
        self.state = RiskAssessmentState.OPEN
        self.finished_at = None
