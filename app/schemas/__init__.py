# Pydantic Schemas
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.schemas.complaint import (
    ComplaintCreate, ComplaintUpdate, ComplaintResponse, 
    ComplaintFeedbackCreate, ComplaintFeedbackResponse,
    ComplaintListResponse, ComplaintStats
)
from app.schemas.location import (
    HospitalResponse, PharmacyResponse, 
    TrafficPointResponse, NearbyLocationResponse
)
from app.schemas.trash import (
    TrashBinResponse, TrashBinUpdate,
    TrashRouteCreate, TrashRouteResponse
)
from app.schemas.disaster import (
    DisasterModeCreate, DisasterModeResponse,
    SafeRouteResponse, BlockedRoadCreate, BlockedRoadResponse
)
from app.schemas.air_quality import AirQualityResponse, AirQualityHeatmapResponse
from app.schemas.shadow import ShadowRouteResponse

__all__ = [
    # User
    "UserCreate", "UserLogin", "UserResponse", "Token",
    # Complaint
    "ComplaintCreate", "ComplaintUpdate", "ComplaintResponse",
    "ComplaintFeedbackCreate", "ComplaintFeedbackResponse",
    "ComplaintListResponse", "ComplaintStats",
    # Location
    "HospitalResponse", "PharmacyResponse",
    "TrafficPointResponse", "NearbyLocationResponse",
    # Trash
    "TrashBinResponse", "TrashBinUpdate",
    "TrashRouteCreate", "TrashRouteResponse",
    # Disaster
    "DisasterModeCreate", "DisasterModeResponse",
    "SafeRouteResponse", "BlockedRoadCreate", "BlockedRoadResponse",
    # Air Quality
    "AirQualityResponse", "AirQualityHeatmapResponse",
    # Shadow
    "ShadowRouteResponse"
]

