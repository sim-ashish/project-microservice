from pydantic import BaseModel
from typing import Optional, Literal

class MessageCreate(BaseModel):
    text: str
    user: str
    group_id: Optional[int] = None
    type: Literal["message", "add", "leave", "video_control"] = "message"
    
    # Video control fields (only used when type="video_control")
    video_action: Optional[Literal["play", "pause", "seek", "change_video"]] = None
    video_name: Optional[str] = None
    video_time: Optional[float] = None  # Current playback time in seconds