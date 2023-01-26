# # Native # #
import json
from uuid import UUID
from typing import Union, Dict, Any, List

# # Installed # #
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from fastapi import APIRouter, Depends

# # Package # #
from app.utils.settings import Params, Page
from app.utils.logger import logger
from app.utils.exceptions import AlreadyExistsException, NotFoundException, BadRequestException
from app.schemas.user import IUserCreate, IUserRead, IUserUpdate, IUserReadTemporary, IUserFilter
from app.database.user import get_current_user
from app.database.session import get_session
from app import crud
from app.models import User
from app.schemas.common import (
    IDeleteResponseBase,
    IGetResponseBase,
    IPostResponseBase,
    IPutResponseBase
)

router = APIRouter()


async def user_filters(filters: Union[str, None] = None) -> Dict[str, Any]:
    try:
        return IUserFilter.parse_obj(json.loads(filters)).dict(exclude_none=True) if filters is not None else {}
    except json.JSONDecodeError:
        raise BadRequestException(detail="Invalid filters")


async def user_scope(scope: Union[str, None] = None) -> List[str]:
    possible_values = list(IUserReadTemporary.schema()['properties'].keys())
    try:
        if scope is None:
            return {}
        scope = scope.split(".")
        if not set(scope).issubset(set(possible_values)):
            raise Exception
        exclude = set(set(possible_values) - set(scope))
        return exclude
    except:
        raise BadRequestException(
            detail=f"Invalid scope. Possible values are: {possible_values}")


@router.get("/user/list", response_model=IGetResponseBase[Page[IUserReadTemporary]])
async def read_users_list(
    params: Params = Depends(),
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user()),
    filters: dict = Depends(user_filters),
    exclude: set = Depends(user_scope)
):
    """
    Retrieve users.
    """
    logger.info(f"filters = {filters}")
    query = None  # TODO build a query in order to get the join data
    if filters:
        query = select(User)
        for key, value in filters.items():
            query = query.where(getattr(User, key) == value)
    users = await crud.user.get_multi_paginated(db_session, params=params, query=query)
    # TODO: fix this. create new class from factory
    IUserReadTemporary.__exclude_fields_custom__ = exclude
    return IGetResponseBase[Page[IUserReadTemporary]](data=users)


@router.post("/user", response_model=IPostResponseBase[IUserReadTemporary])
async def create_user(
    new_user: IUserCreate,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    user = await crud.user.get_by_email(db_session, email=new_user.email)
    if user:
        raise AlreadyExistsException
    # TODO assign default roles to user
    user = await crud.user.create(db_session, obj_in=new_user)
    # TODO send email to user with password
    return IPostResponseBase[IUserReadTemporary](data=user)


@router.patch("/user/{user_id}", response_model=IPutResponseBase[IUserReadTemporary])
async def update_user(
    user_id: UUID,
    new_user: IUserUpdate,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=False)),
):
    user = await crud.user.get(db_session=db_session, id=user_id)
    if not user:
        raise NotFoundException
    user_updated = await crud.user.update(
        db_session=db_session, obj_current=user, obj_new=new_user
    )
    return IPutResponseBase[IUserReadTemporary](data=user_updated)


@router.patch("/user/{user_id}/role/{role_id}", response_model=IPutResponseBase[IUserRead])
async def update_user_role(
    role_id: UUID,
    user_id: UUID,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    role = await crud.role.get(db_session, id=role_id)
    await crud.user.update_role(db_session, id=user_id, role=role)
    # TODO remove abundant database call
    user = await crud.user.get(db_session, id=user_id)
    return IPutResponseBase[IUserRead](data=user)


@router.patch("/user/{user_id}/team/{team_id}", response_model=IPutResponseBase[IUserRead])
async def update_user_team(
    team_id: UUID,
    user_id: UUID,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    team = await crud.team.get(db_session, id=team_id)
    await crud.user.update_team(db_session, id=user_id, team=team)
    # TODO remove abundant database call
    user = await crud.user.get(db_session, id=user_id)
    return IPutResponseBase[IUserRead](data=user)


@router.patch("/user/{user_id}/visibility_group/{visibility_group_id}", response_model=IPutResponseBase[IUserRead])
async def update_user_visibility_group(
    visibility_group_id: UUID,
    user_id: UUID,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    visibility_group = await crud.visibility_group.get(db_session, id=visibility_group_id)
    await crud.user.update_visibility_group(db_session, id=user_id, visibility_group=visibility_group)
    # TODO remove abundant database call
    user = await crud.user.get(db_session, id=user_id)
    return IPutResponseBase[IUserRead](data=user)


@router.get("/user/{user_id}", response_model=IGetResponseBase[IUserRead])
async def get_user_by_id(
    user_id: UUID,
    db_session: AsyncSession = Depends(get_session),
):
    user = await crud.user.get(db_session, id=user_id)
    return IGetResponseBase[IUserRead](data=user)


@router.delete("/user/{user_id}", response_model=IDeleteResponseBase[IUserRead])
async def delete_user(
    user_id: UUID,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    if current_user.id == user_id:
        raise BadRequestException(detail="You cannot delete yourself")

    user = await crud.user.get(db_session=db_session, id=user_id)
    if not user:
        raise NotFoundException
    user = await crud.user.remove(db_session, id=user_id)
    return IDeleteResponseBase[IUserRead](
        data=user
    )


@router.get("/user", response_model=IGetResponseBase[IUserRead])
async def get_my_data(
    current_user: User = Depends(get_current_user()),
):
    # TODO: assign applications to user based on region or role
    # TODO: not to return sensitive data
    current_user.applications = ['delorean', 'cms', 'crme', 'kops', 'jorge/inbound', 'jorge']
    return IGetResponseBase[IUserRead](data=current_user)
