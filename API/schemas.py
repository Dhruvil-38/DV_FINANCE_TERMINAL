from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Auth ----------

class LoginRequest(BaseModel):
    email: str
    password: str


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
    name: str
    email: str
    phone: Optional[str] = None
    tier: str = "Standard"
    status: str = "Active"
    assigned_analyst: Optional[str] = None
    aum: float = 0.0


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    joined_at: datetime


# ---------- Trade calls ----------

class TradeCallBase(BaseModel):
    symbol: str
    sector: str = "Unclassified"
    direction: str  # LONG | SHORT
    entry: float
    stop_loss: float
    target: float
    notes: str = ""


class TradeCallCreate(TradeCallBase):
    pass


class TradeCallUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    result_pct: Optional[float] = None


class TradeCallOut(TradeCallBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    result_pct: Optional[float]
    created_by: str
    created_at: datetime
    closed_at: Optional[datetime]


# ---------- Watchlist ----------

class WatchlistCreate(BaseModel):
    symbol: str
    sector: str = "Unclassified"
    last_price: float = 0.0
    day_change_pct: float = 0.0


class WatchlistOut(WatchlistCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    added_by: Optional[str]
    added_at: datetime


# ---------- News ----------

class NewsCreate(BaseModel):
    category: str  # MARKET | COMPANY | FIRM
    title: str
    body: str = ""
    source: str = "DV Finance Desk"


class NewsOut(NewsCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: Optional[str]
    published_at: datetime


# ---------- Research notes ----------

class ResearchNoteCreate(BaseModel):
    title: str
    body: str = ""
    client_id: Optional[int] = None
    call_id: Optional[int] = None


class ResearchNoteOut(ResearchNoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: str
    created_at: datetime


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "TODO"
    priority: str = "MEDIUM"
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskOut(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ---------- Documents ----------

class DocumentCreate(BaseModel):
    filename: str
    category: str = "General"
    size_kb: float = 0.0
    client_id: Optional[int] = None


class DocumentOut(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uploaded_by: str
    uploaded_at: datetime
