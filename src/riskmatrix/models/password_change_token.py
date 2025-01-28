import secrets
import uuid
from datetime import datetime
from datetime import timedelta
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped

from ..orm.meta import Base
from ..orm.meta import DateTimeNoTz
from ..orm.meta import UUIDStr
from ..orm.meta import UUIDStrPK
from ..security_policy import PasswordException


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User


class PasswordChangeToken(Base):

    __tablename__ = 'password_change_tokens'

    id: Mapped[UUIDStrPK]
    user_id: Mapped[UUIDStr] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE'),
        index=True
    )
    time_requested: Mapped[DateTimeNoTz]
    time_consumed: Mapped[DateTimeNoTz | None]
    time_expired: Mapped[DateTimeNoTz | None]
    token: Mapped[str]
    ip_address: Mapped[str]

    user: Mapped['User'] = relationship(lazy='joined')

    def __init__(
        self,
        user:           'User',
        ip_address:     str,
        time_requested: datetime | None = None
    ):

        if not user.email:
            raise PasswordException(
                'Cannot request password change without an email.'
            )
        self.id = str(uuid.uuid4())
        self.user = user
        self.ip_address = ip_address

        if time_requested is None:
            time_requested = datetime.utcnow()
        self.time_requested = time_requested.replace(tzinfo=None)
        self.time_consumed = None
        self.token = secrets.token_urlsafe()

    def consume(self, email: str) -> None:
        if self.consumed:
            msg = f'Token "{self.token}" has already been used'
            raise PasswordException(msg)

        user_email = self.user.email
        assert user_email

        if email and email.lower() != user_email.lower():
            raise PasswordException(f'Invalid email for token "{self.token}"')

        # Initial password set link does not expire
        if self.user.password and self.expired:
            raise PasswordException(f'Token "{self.token}" has expired')

        time_consumed = datetime.utcnow()
        time_consumed = time_consumed.replace(tzinfo=None)
        self.time_consumed = time_consumed

    @property
    def consumed(self) -> bool:
        if self.time_consumed is not None:
            return True
        return False

    def expire(self, expired: datetime | None = None) -> None:
        if not self.expired:
            if not expired:
                expired = datetime.utcnow()
            expired = expired.replace(tzinfo=None)
            self.time_expired = expired

    @property
    def expired(self) -> bool:
        expired = self.time_expired
        if expired and expired < datetime.utcnow():
            return True

        expiring_time = self.time_requested + timedelta(hours=48)
        if datetime.utcnow() > expiring_time:
            return True
        return False
