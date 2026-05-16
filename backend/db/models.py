"""
T2: Pydantic数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ===== 请求模型 =====
class CreateSessionRequest(BaseModel):
    city_name: str = Field(..., description="城市名称")
    days: int = Field(default=3, ge=1, le=14, description="游玩天数")


class ScoreRequest(BaseModel):
    session_id: str
    score: int = Field(default=3, ge=1, le=5)
    gesture: str = Field(default="tap_star", pattern="^(swipe_right|swipe_left|swipe_up|swipe_down|tap_star)$")


class UpdatePreferenceRequest(BaseModel):
    num_people: Optional[int] = Field(default=None, ge=1)
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    accommodation: Optional[str] = None
    transport_mode: Optional[str] = Field(default=None, pattern="^(bus|taxi|self_drive|bike|walk)$")
    pace: Optional[str] = Field(default=None, pattern="^(relaxed|standard|compact)$")
    food_preference: Optional[str] = None
    budget_per_day: Optional[int] = Field(default=None, ge=0)
    special_requirements: Optional[str] = None


class RunPlannerRequest(BaseModel):
    session_id: str


class AdjustPlannerRequest(BaseModel):
    session_id: str
    action: str = Field(..., pattern="^(add|remove|change_pace|change_budget|replan)$")
    poi_id: Optional[str] = None
    pace: Optional[str] = Field(default=None, pattern="^(relaxed|standard|compact)$")
    budget_per_day: Optional[int] = Field(default=None, ge=0)


# ===== 响应模型 =====
class APIResponse(BaseModel):
    ok: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None


class CardPOI(BaseModel):
    poi_id: str
    name: str
    type: str
    rating: float
    rating_count: int
    tags: list
    avg_cost: int
    duration_min: int
    district: str
    lat: float
    lon: float
    summary: str = ""
