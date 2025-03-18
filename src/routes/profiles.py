import requests
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    status,
    HTTPException,
)
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config import get_jwt_auth_manager
from database import (
    get_db,
    UserProfileModel, UserModel,
)
from exceptions import BaseSecurityError
from schemas.examples.movies import actor_schema_example
from schemas.profiles import ProfileResponseSchema, ProfileCreateSchema
from security.interfaces import JWTAuthManagerInterface

router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema
)
async def create_profile(
        user_data: ProfileCreateSchema,
        access_token: str = Depends(oauth2_scheme),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: AsyncSession = Depends(get_db),
):
    if not access_token:
        raise HTTPException(status_code=401,
                            detail="Authorization header is missing")
    try:
        check_token = jwt_manager.decode_access_token(access_token)
        user_id = check_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error)
        )

    find_user_res = await db.execute(select(UserModel).where(
        UserModel.id == user_id
    ))
    find_user = find_user_res.scalars().first()

    if not find_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active."
        )

    if find_user.group_id == 1 and find_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile."
        )

    profile_res = await db.execute(select(UserProfileModel).options(
        joinedload(UserProfileModel.user)).where(
        UserProfileModel.user_id == user_id))

    find_user_profile = profile_res.scalars().first()

    if find_user_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User already has a profile.")

    try:
        new_profile = UserProfileModel(
                user_id=user_id,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                gender=user_data.gender,
                date_of_birth=user_data.date_of_birth,
                info=user_data.info,
                avatar=user_data.avatar
        )
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return new_profile

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later."
        )


class TestData(BaseModel):
    data: str
    message: str = "Helloloo"

@router.post("/test", response_model=TestData)
async def test_profile(
        payload: TestData,
        db: AsyncSession = Depends(get_db)
):
    return payload

@router.get("/users/{user_id}/profile/")
async def read_profile(
        user_id: int,
        db: AsyncSession = Depends(get_db),
):
    find_user_res = await db.execute(select(UserModel).where(
        UserModel.id == user_id
    ))
    find_user = find_user_res.scalars().first()

    if not find_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User doesn't exist."
        )

    profile_res = await db.execute(select(UserProfileModel).options(
        joinedload(UserProfileModel.user)).where(
        UserProfileModel.user_id == user_id))

    find_user_profile = profile_res.scalars().first()

    if not find_user_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile for user doesn't exist.")

    return find_user_profile


@router.post("/uploads/")
async def upload_image(image: UploadFile, db: AsyncSession = Depends(get_db)):
    file = image.file
    filename = image.filename
    with open(f"unique_{filename}", "wb") as f:
        f.write(file.read())
    return {"message": "Your avatar uploaded"}


def iterfile(image_name):
    with open(image_name, "rb") as image:
        while chunk := image.read(1024 * 1024):
            yield chunk


@router.get("/uploads/{image_name}/")
async def get_image(image_name: str):
    return StreamingResponse(
        iterfile(image_name),
        media_type="image"
    )
