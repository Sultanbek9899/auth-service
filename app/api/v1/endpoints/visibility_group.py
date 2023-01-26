# # Native # #
from uuid import UUID

# # Installed # #
import sqlalchemy
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer

# # Package # #
from app.utils.security import verify_jwt_token
from app.utils.settings import Params, Page, settings
from app.utils.exceptions import NotFoundException, AlreadyExistsException, BadRequestException
from app.models.user import User
from app.schemas.common import IDeleteResponseBase, IGetResponseBase, IPostResponseBase, IPutResponseBase
from app.schemas.visibility_group import *
from app import crud
from app.database.user import get_current_user
from app.database.session import get_session
from app.utils.logger import logger
from app.utils.constants import VISIBILITY_GROUP_ENTITY_POSSIBLE_VALUES

router = APIRouter()

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.HOSTNAME}/api/auth/access-token"
)


@router.get("/visibility_group/list", response_model=IGetResponseBase[Page[IVisibilityGroupRead]])
async def get_visibility_group_list(
    params: Params = Depends(),
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user()),
):
    visibility_groups = await crud.visibility_group.get_multi_paginated(db_session, params=params)
    return IGetResponseBase[Page[IVisibilityGroupRead]](data=visibility_groups)


# TODO: add response model
@router.get("/visibility_group/settings")
async def get_visibility_group_settings(
    request: Request,
    db_session: AsyncSession = Depends(get_session),
):
    data = await request.app.visibility_group.get(db_session)
    logger.debug(f"get_visibility_group_settings: {data}")
    return data


@router.get("/visibility_group/validate/{visibility_group_entity}", response_model=IGetResponseBase[IVisibilityGroupValidateResponse])
async def validate(
    request: Request,
    visibility_group_entity: str,
    access_token: str = Depends(reusable_oauth2),
    db_session: AsyncSession = Depends(get_session),
):

    visibility_group_entity = visibility_group_entity.lower().strip()
    if visibility_group_entity not in VISIBILITY_GROUP_ENTITY_POSSIBLE_VALUES:
        raise BadRequestException(
            detail=f'Invalid value: {visibility_group_entity}. Possible values: {VISIBILITY_GROUP_ENTITY_POSSIBLE_VALUES}')

    data = await request.app.visibility_group.validate(
        db_session=db_session,
        visibility_group_entity=visibility_group_entity,
        access_token=access_token
    )

    meta = await verify_jwt_token(token=access_token, type="access", db_session=db_session)

    return IGetResponseBase[IVisibilityGroupValidateResponse](meta=meta, data=data)


@ router.get("/visibility_group/{visibility_group_id}", response_model=IGetResponseBase[IVisibilityGroupRead])
async def get_visibility_group_by_id(
    visibility_group_id: UUID,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user()),
):
    visibility_group = await crud.visibility_group.get(db_session, id=visibility_group_id)
    if not visibility_group:
        raise NotFoundException
    return IGetResponseBase[IVisibilityGroupRead](data=visibility_group)


@ router.post("/visibility_group", response_model=IPostResponseBase[IVisibilityGroupRead])
async def create_visibility_group(
    visibility_group: IVisibilityGroupCreate,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    if await crud.visibility_group.get_visibility_group_by_prefix(db_session, prefix=visibility_group.prefix):
        raise AlreadyExistsException
    visibility_group = await crud.visibility_group.create(db_session, obj_in=visibility_group, created_by=current_user.id)
    return IPostResponseBase[IVisibilityGroupRead](data=visibility_group)


@ router.patch("/visibility_group/{visibility_group_id}", response_model=IPostResponseBase[IVisibilityGroupRead])
async def update_visibility_group(
    visibility_group_id: UUID,
    visibility_group: IVisibilityGroupUpdate,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),
):
    current_visibility_group = await crud.visibility_group.get(db_session=db_session, id=visibility_group_id)
    if not current_visibility_group:
        raise NotFoundException
    visibility_group.updated_by = current_user.id
    try:
        visibility_group_updated = await crud.visibility_group.update(
            db_session=db_session,
            obj_current=current_visibility_group,
            obj_new=visibility_group
        )
    except sqlalchemy.exc.IntegrityError as e:
        raise BadRequestException(detail=f"Visibility group update failed: {e}")
    return IPutResponseBase[IVisibilityGroupRead](data=visibility_group_updated)


@router.delete("/visibility_group/{visibility_group_id}", response_model=IDeleteResponseBase[IVisibilityGroupRead])
async def remove_visibility_group(
    visibility_group_id: UUID,
    db_session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user(required_permissions=True)),

):
    current_visibility_group = await crud.visibility_group.get(db_session=db_session, id=visibility_group_id)
    if not current_visibility_group:
        raise NotFoundException
    visibility_group = await crud.visibility_group.remove(db_session, id=visibility_group_id)
    return IDeleteResponseBase[IVisibilityGroupRead](data=visibility_group)
