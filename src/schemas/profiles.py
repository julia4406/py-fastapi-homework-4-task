from datetime import date

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl, ConfigDict

from database.models.accounts import GenderEnum
from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date
)



class ProfileBaseSchema(BaseModel):
    first_name: str
    last_name: str
    avatar: str
    gender: GenderEnum
    date_of_birth: date
    info: str

    class Config:
        from_attributes = True


class ProfileResponseSchema(ProfileBaseSchema):
    id: int
    user_id: int


class ProfileCreateSchema(ProfileBaseSchema):

    @field_validator("first_name", "last_name")
    def names_validator(cls, value):
        return validate_name(value)

    # @field_validator("avatar")
    # def avatar_validator(cls, value):
    #     return validate_image(value)

    @field_validator("gender")
    def gender_validator(cls, value):
        return validate_gender(value)

    @field_validator("date_of_birth")
    def date_of_birth_validator(cls, value):
        return validate_birth_date(value)

    @field_validator("info")
    def info_validator(cls, value):
        if value.strip():
            return value
        raise ValueError("This field cannot be empty. Fill the data.")

