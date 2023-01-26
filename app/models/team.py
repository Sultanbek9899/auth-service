# # Native # #
from typing import List, Optional

# # Installed # #
from sqlmodel import Field, Relationship, SQLModel

# # Package # #
from app.models.base_uuid_model import BaseUUIDModel
from app.models.links import LinkTeamUser

__all__ = (
    "Team",
)


class TeamBase(SQLModel):
    name: str = Field(index=True, sa_column_kwargs={"unique": True})


class Team(BaseUUIDModel, TeamBase, table=True):
    # users: List["User"] = Relationship(back_populates="team")
    users: Optional[List["User"]] = Relationship(
        back_populates="teams", link_model=LinkTeamUser)
