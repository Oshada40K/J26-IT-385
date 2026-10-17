import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

Password = Annotated[str, Field(min_length=12, max_length=128)]


class EmailInput(BaseModel):
    email: str = Field(max_length=254)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+', value):
            raise ValueError('Enter a valid email address.')
        return value


class RegisterInput(EmailInput):
    full_name: str = Field(min_length=2, max_length=100)
    password: Password

    @field_validator('full_name')
    @classmethod
    def clean_name(cls, value):
        value = ' '.join(value.split())
        if len(value) < 2:
            raise ValueError('Enter your full name.')
        return value


class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class ResetInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: Password


class User(BaseModel):
    id: str
    full_name: str
    email: str


class Session(BaseModel):
    user: User
    expires_at: int
