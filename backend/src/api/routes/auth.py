"""
Authentication API routes.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, EmailStr

router = APIRouter()


# Request/Response Models
class UserRegistration(BaseModel):
    """User registration model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    full_name: str = Field(..., description="User's full name")
    institution: Optional[str] = Field(None, description="User's institution")
    research_area: Optional[str] = Field(None, description="Research area of interest")


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserProfile(BaseModel):
    """User profile model."""
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    institution: Optional[str] = Field(None, description="User's institution")
    research_area: Optional[str] = Field(None, description="Research area")
    role: str = Field(default="user", description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime = Field(..., description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")


class AuthToken(BaseModel):
    """Authentication token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserProfile = Field(..., description="User profile information")


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


# Mock user data for demo
MOCK_USERS = {
    "demo@oceanquery.com": {
        "user_id": "user_demo_001",
        "email": "demo@oceanquery.com",
        "password": "demo123",  # In real app, this would be hashed
        "full_name": "Demo User",
        "institution": "OceanQuery Demo",
        "research_area": "Ocean Data Analysis",
        "role": "user",
        "is_active": True,
        "created_at": datetime(2024, 1, 1, 10, 0, 0),
        "last_login": None
    },
    "researcher@marine.org": {
        "user_id": "user_researcher_001",
        "email": "researcher@marine.org", 
        "password": "research123",
        "full_name": "Dr. Marine Researcher",
        "institution": "Marine Research Institute",
        "research_area": "Physical Oceanography",
        "role": "researcher",
        "is_active": True,
        "created_at": datetime(2024, 1, 15, 14, 30, 0),
        "last_login": datetime(2024, 11, 1, 9, 15, 0)
    }
}


@router.post("/register", response_model=AuthToken)
async def register_user(user_data: UserRegistration):
    """Register a new user account."""
    # Check if user already exists
    if user_data.email in MOCK_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user (in real app, hash password and save to database)
    user_id = f"user_{int(datetime.utcnow().timestamp())}"
    
    new_user = {
        "user_id": user_id,
        "email": user_data.email,
        "password": user_data.password,  # Would be hashed in real app
        "full_name": user_data.full_name,
        "institution": user_data.institution,
        "research_area": user_data.research_area,
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    MOCK_USERS[user_data.email] = new_user
    
    # Create user profile for response
    user_profile = UserProfile(
        user_id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        institution=user_data.institution,
        research_area=user_data.research_area,
        role="user",
        is_active=True,
        created_at=datetime.utcnow(),
        last_login=None
    )
    
    # Return mock token (in real app, generate JWT)
    return AuthToken(
        access_token=f"mock_token_{user_id}",
        token_type="bearer",
        expires_in=3600,
        user=user_profile
    )


@router.post("/login", response_model=AuthToken)
async def login_user(login_data: UserLogin):
    """Authenticate user and return access token."""
    # Check if user exists and password matches
    user = MOCK_USERS.get(login_data.email)
    if not user or user["password"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Update last login
    user["last_login"] = datetime.utcnow()
    
    # Create user profile for response
    user_profile = UserProfile(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        institution=user.get("institution"),
        research_area=user.get("research_area"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user["last_login"]
    )
    
    # Return mock token (in real app, generate JWT)
    return AuthToken(
        access_token=f"mock_token_{user['user_id']}",
        token_type="bearer", 
        expires_in=3600,
        user=user_profile
    )


@router.post("/refresh", response_model=AuthToken)
async def refresh_token(refresh_data: TokenRefresh):
    """Refresh access token using refresh token."""
    # Mock token refresh (in real app, validate refresh token)
    if not refresh_data.refresh_token.startswith("mock_refresh_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Extract user ID from mock token
    try:
        user_id = refresh_data.refresh_token.split("_")[-1]
        # Find user by ID (simplified for demo)
        user = next(u for u in MOCK_USERS.values() if u["user_id"] == f"user_{user_id}")
    except (IndexError, StopIteration):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_profile = UserProfile(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        institution=user.get("institution"),
        research_area=user.get("research_area"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )
    
    return AuthToken(
        access_token=f"mock_token_{user['user_id']}",
        token_type="bearer",
        expires_in=3600,
        user=user_profile
    )


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(token: str = Depends(lambda: "mock_token_user_demo_001")):
    """Get current user's profile information."""
    # Extract user ID from token (simplified for demo)
    if not token.startswith("mock_token_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = token.replace("mock_token_", "")
    
    # Find user by ID (simplified for demo)
    try:
        user = next(u for u in MOCK_USERS.values() if u["user_id"] == user_id)
    except StopIteration:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserProfile(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        institution=user.get("institution"),
        research_area=user.get("research_area"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )


@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    full_name: Optional[str] = None,
    institution: Optional[str] = None,
    research_area: Optional[str] = None,
    token: str = Depends(lambda: "mock_token_user_demo_001")
):
    """Update user profile information."""
    # Extract user ID from token
    if not token.startswith("mock_token_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = token.replace("mock_token_", "")
    
    # Find and update user
    try:
        user = next(u for u in MOCK_USERS.values() if u["user_id"] == user_id)
        
        if full_name is not None:
            user["full_name"] = full_name
        if institution is not None:
            user["institution"] = institution
        if research_area is not None:
            user["research_area"] = research_area
            
    except StopIteration:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserProfile(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        institution=user.get("institution"),
        research_area=user.get("research_area"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )


@router.post("/logout")
async def logout_user(token: str = Depends(lambda: "mock_token_user_demo_001")):
    """Logout user and invalidate token."""
    # In real app, add token to blacklist
    return {"message": "Successfully logged out"}


@router.get("/demo-login", response_model=AuthToken)
async def demo_login():
    """Demo login endpoint for development/testing."""
    # Get demo user
    user = MOCK_USERS["demo@oceanquery.com"]
    user["last_login"] = datetime.utcnow()
    
    user_profile = UserProfile(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        institution=user.get("institution"),
        research_area=user.get("research_area"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user["last_login"]
    )
    
    return AuthToken(
        access_token=f"mock_token_{user['user_id']}",
        token_type="bearer",
        expires_in=3600,
        user=user_profile
    )
