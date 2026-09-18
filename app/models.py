"""Pydantic API and normalized registrar models."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AllotmentStatus(str, Enum):
    ALLOTTED = "allotted"
    NOT_ALLOTTED = "not_allotted"
    NOT_APPLIED = "not_applied"
    LOOKUP_FAILED = "lookup_failed"


class CheckRequest(BaseModel):
    pan: str = Field(..., description="10-character PAN")
    ipo: str = Field(..., description="Current IPO name, registrar client id, or Peek slug")


class CheckResponse(BaseModel):
    pan: str
    ipo: str
    registrar: str
    status: AllotmentStatus
    shares_allotted: Optional[int] = None
    message: str
    checked_at: str


class RegistrarResult(BaseModel):
    status: AllotmentStatus
    shares_allotted: Optional[int] = None
    message: str
