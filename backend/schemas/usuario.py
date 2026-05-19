from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str