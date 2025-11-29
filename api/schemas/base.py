"""
Base Schemas
============

Customized Pydantic BaseModel with automatic snake_case <-> camelCase conversion.
Uses Pydantic's official alias_generators.
"""

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class BaseModel(PydanticBaseModel):
    """
    Enhanced BaseModel with automatic snake_case to camelCase conversion.

    All schemas inheriting from this BaseModel will automatically:
    - Convert snake_case field names to camelCase in JSON output
    - Accept both snake_case and camelCase in input
    - Read from ORM models seamlessly

    Usage:
        from api.schemas.base import BaseModel

        class UserInfo(BaseModel):
            user_name: str
            created_at: datetime
            is_active: bool

        # From ORM:
        user = User(user_name="admin", created_at=datetime.now(), is_active=True)
        info = UserInfo.model_validate(user)

        # JSON output (automatic camelCase):
        info.model_dump()  # {"userName": "admin", "createdAt": "...", "isActive": true}

        # Also accepts camelCase input:
        UserInfo(userName="admin", createdAt=datetime.now(), isActive=True)  # Works!
    """
    model_config = ConfigDict(
        alias_generator=to_camel,      # auto convert snake_case -> camelCase
        populate_by_name=True,          # accept both snake_case and camelCase
        from_attributes=True,           # read from ORM models
    )
