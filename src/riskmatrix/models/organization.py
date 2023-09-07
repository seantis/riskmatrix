from pyramid.authorization import Allow
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from uuid import uuid4

from riskmatrix.orm.meta import Base
from riskmatrix.orm.meta import str_256
from riskmatrix.orm.meta import UUIDStrPK


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from riskmatrix.models import User
    from riskmatrix.types import ACL


class Organization(Base):

    __tablename__ = 'organization'

    id: Mapped[UUIDStrPK]
    name: Mapped[str_256]
    email: Mapped[str_256]

    users: Mapped[list['User']] = relationship(
        back_populates='organization',
    )

    def __init__(self, name: str, email: str):
        self.id = str(uuid4())
        self.name = name
        self.email = email

    def __acl__(self) -> list['ACL']:
        return [
            (Allow, f'org_{self.id}', ['view']),
        ]
