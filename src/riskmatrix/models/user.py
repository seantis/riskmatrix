import bcrypt
from datetime import datetime
from sedate import utcnow
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from uuid import uuid4

from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import str_128
from riskmatrix.orm.meta import str_256
from riskmatrix.orm.meta import str_32
from riskmatrix.orm.meta import UUIDStr
from riskmatrix.orm.meta import UUIDStrPK


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.models import Organization


class User(Base):

    __tablename__ = 'user'

    id: Mapped[UUIDStrPK]
    organization_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE'),
        index=True,
    )
    first_name: Mapped[str_256 | None]
    last_name: Mapped[str_256 | None]
    email: Mapped[str_256] = mapped_column(unique=True)
    locale: Mapped[str_32]
    password: Mapped[str_128 | None]
    modified: Mapped[datetime | None] = mapped_column(
        onupdate=utcnow
    )
    last_login: Mapped[datetime | None]
    last_password_change: Mapped[datetime | None]

    organization: Mapped['Organization'] = relationship(
        back_populates='users',
        lazy='joined',
    )

    def __init__(
        self,
        email:        str,
        organization: 'Organization',
        password:     str | None = None,
        first_name:   str | None = None,
        last_name:    str | None = None,
        locale:       str = 'en'
    ):
        self.id = str(uuid4())
        self.email = email
        self.organization = organization
        self.first_name = first_name
        self.last_name = last_name
        self.locale = locale

        if password is not None:
            self.set_password(password)

    @property
    def fullname(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        if not parts:
            return self.email
        return ' '.join(parts)

    def set_password(self, password: str) -> None:
        password = password or ''
        pwhash = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        self.password = pwhash.decode('utf8')
        self.last_password_change = utcnow()

    def check_password(self, password: str) -> bool:
        if not self.password:
            return False
        try:
            return bcrypt.checkpw(
                password.encode('utf8'),
                self.password.encode('utf8')
            )
        except (AttributeError, ValueError):
            return False

    def groups(self) -> list[str]:
        return [f'org_{self.organization.id}']
