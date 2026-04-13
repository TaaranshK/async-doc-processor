"""
Data models for login and registration.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


# -------
# Request models
# -------

class RegisterRequest(BaseModel):
    email:    EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# -------
# Response models
# -------

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class UserResponse(BaseModel):
    id:    uuid.UUID
    email: EmailStr

    model_config = {"from_attributes": True}