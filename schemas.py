"""
Database Schemas for Grandline Fanverse

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercase of the class name (e.g., PirateCrew -> "piratecrew").
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Marine(BaseModel):
    name: str = Field(..., description="Marine's full name")
    rank: str = Field(..., description="Rank within the Marines")
    bio: Optional[str] = Field(None, description="Short biography or notes")
    avatar_url: Optional[str] = Field(None, description="Image URL")

class PirateCrew(BaseModel):
    name: str = Field(..., description="Crew name")
    sea: str = Field(..., description="Sea/Region: East Blue, West Blue, North Blue, South Blue, Grand Line")
    description: Optional[str] = Field(None, description="Crew description")
    emblem_url: Optional[str] = Field(None, description="Crew emblem image URL")
    crew_of_month: bool = Field(False, description="Highlighted as crew of the month")

class PirateMember(BaseModel):
    crew_id: str = Field(..., description="Reference to PirateCrew _id as string")
    name: str = Field(..., description="Member name")
    role: Optional[str] = Field(None, description="Role within the crew")
    bounty: int = Field(0, ge=0, description="Bounty in Beli")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")

class EventResultItem(BaseModel):
    category: str
    winner: str
    runner_up: Optional[str] = None
    notes: Optional[str] = None

class Event(BaseModel):
    title: str
    description: Optional[str] = None
    date: datetime
    status: str = Field("upcoming", description="upcoming | ongoing | completed")
    banner_url: Optional[str] = None
    results: Optional[List[EventResultItem]] = None

# Optional: Leaderboard entries can be computed from PirateMember by bounty,
# so no dedicated collection is required.
