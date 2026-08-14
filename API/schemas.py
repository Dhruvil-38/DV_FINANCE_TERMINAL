from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field

Direction = Literal["LONG", "SHORT"]
CallStatus = Literal["ACTIVE", "TARGET_HIT", "SL_HIT", "CLOSED", "CANCELLED"]
NewsCategory = Literal["MARKET", "COMPANY", "FIRM"]
ClientTier = Literal["Standard", "Premium", "Institutional"]
ClientStatus = Literal["Active", "Onboarding", "Dormant"]
TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE"]
TaskPriority = Literal["LOW", "MEDIUM", "HIGH"]
DocumentCategory = Literal["Research", "Compliance", "Client", "General"]

MAX_BODY_LENGTH = 20_000


# ---------- Auth ----------

class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: int
    client_id: Optional[int] = None


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    client_id: Optional[int] = None


# ---------- Clients ----------

class ClientBase(BaseModel):
    name: str = Field(max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=32)
    tier: ClientTier = "Standard"
    status: ClientStatus = "Active"
    assigned_analyst: Optional[str] = Field(default=None, max_length=200)
    aum: float = Field(default=0.0, ge=0)


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    joined_at: datetime


# ---------- Trade calls ----------

class TradeCallBase(BaseModel):
    symbol: str = Field(max_length=32)
    sector: str = Field(default="Unclassified", max_length=64)
    direction: Direction
    entry: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    target: float = Field(gt=0)
    notes: str = Field(default="", max_length=MAX_BODY_LENGTH)


class TradeCallCreate(TradeCallBase):
    pass


class TradeCallUpdate(BaseModel):
    status: Optional[CallStatus] = None
    notes: Optional[str] = Field(default=None, max_length=MAX_BODY_LENGTH)
    result_pct: Optional[float] = None


class TradeCallOut(TradeCallBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: CallStatus
    result_pct: Optional[float]
    created_by: str
    created_at: datetime
    closed_at: Optional[datetime]


# ---------- Watchlist ----------

class WatchlistCreate(BaseModel):
    symbol: str = Field(max_length=32)
    sector: str = Field(default="Unclassified", max_length=64)
    last_price: float = Field(default=0.0, ge=0)
    day_change_pct: float = 0.0


class WatchlistOut(WatchlistCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    added_by: Optional[str]
    added_at: datetime


# ---------- News ----------

class NewsCreate(BaseModel):
    category: NewsCategory
    title: str = Field(max_length=200)
    body: str = Field(default="", max_length=MAX_BODY_LENGTH)
    source: str = Field(default="DV Finance Desk", max_length=120)


class NewsOut(NewsCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: Optional[str]
    published_at: datetime


# ---------- Research notes ----------

class ResearchNoteCreate(BaseModel):
    title: str = Field(max_length=200)
    body: str = Field(default="", max_length=MAX_BODY_LENGTH)
    client_id: Optional[int] = Field(default=None, ge=1)
    call_id: Optional[int] = Field(default=None, ge=1)


class ResearchNoteOut(ResearchNoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: str
    created_at: datetime


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=MAX_BODY_LENGTH)
    status: TaskStatus = "TODO"
    priority: TaskPriority = "MEDIUM"
    assigned_to: Optional[str] = Field(default=None, max_length=200)
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[str] = Field(default=None, max_length=200)
    due_date: Optional[datetime] = None


class TaskOut(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ---------- Documents ----------

class DocumentCreate(BaseModel):
    filename: str = Field(max_length=200)
    category: DocumentCategory = "General"
    size_kb: float = Field(default=0.0, ge=0)
    client_id: Optional[int] = Field(default=None, ge=1)


class DocumentOut(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uploaded_by: str
    uploaded_at: datetime
