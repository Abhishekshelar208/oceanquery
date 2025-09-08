"""
Chat API routes for AI-powered natural language queries.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.core.config import settings


router = APIRouter()


# Request/Response Models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User's natural language query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    include_sql: bool = Field(default=True, description="Include generated SQL in response")
    max_results: int = Field(default=100, description="Maximum number of results to return")


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str = Field(..., description="AI assistant response")
    sql_query: Optional[str] = Field(None, description="Generated SQL query")
    data: Optional[dict] = Field(None, description="Query results data")
    conversation_id: str = Field(..., description="Conversation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class ConversationHistory(BaseModel):
    """Conversation history model."""
    conversation_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


# Mock data for development
MOCK_RESPONSES = {
    "temperature": {
        "message": "I found temperature data for your query. Based on ARGO float measurements:\n\n🌡️ Average sea surface temperature: 28.5°C\n📊 Temperature range: 15-32°C at surface\n📈 Found 1,247 temperature profiles\n\n*Analysis shows typical tropical ocean stratification with a thermocline around 100m depth.*",
        "sql_query": """
SELECT 
    float_id,
    measurement_date,
    latitude,
    longitude,
    pressure,
    temperature
FROM argo_profiles 
WHERE temperature IS NOT NULL
  AND latitude BETWEEN -10 AND 30
  AND longitude BETWEEN 60 AND 100
  AND measurement_date >= '2023-03-01'
ORDER BY measurement_date DESC, pressure ASC
LIMIT 1000;
        """.strip(),
        "data": {
            "total_profiles": 1247,
            "avg_surface_temp": 28.5,
            "temp_range": {"min": 15.2, "max": 32.1},
            "depth_range": {"min": 0, "max": 2000},
            "sample_profiles": [
                {"float_id": "2902755", "lat": 10.5, "lon": 77.2, "surface_temp": 29.1},
                {"float_id": "2902756", "lat": 8.3, "lon": 73.1, "surface_temp": 28.7},
                {"float_id": "2902757", "lat": 12.7, "lon": 79.5, "surface_temp": 27.9}
            ]
        }
    },
    "salinity": {
        "message": "Here's the salinity analysis from ARGO data:\n\n💧 Average salinity: 35.2 PSU\n🌊 Salinity range: 33.8 - 37.1 PSU\n📍 Geographic coverage: Indian Ocean\n📊 Found 892 salinity profiles\n\n*Data shows typical Arabian Sea high salinity and Bay of Bengal low salinity patterns.*",
        "sql_query": """
SELECT 
    float_id,
    measurement_date,
    latitude,
    longitude,
    pressure,
    salinity
FROM argo_profiles 
WHERE salinity IS NOT NULL
  AND latitude BETWEEN 0 AND 25
  AND longitude BETWEEN 65 AND 95
ORDER BY measurement_date DESC, pressure ASC
LIMIT 1000;
        """.strip(),
        "data": {
            "total_profiles": 892,
            "avg_salinity": 35.2,
            "salinity_range": {"min": 33.8, "max": 37.1},
            "regional_stats": {
                "arabian_sea": {"avg": 36.5, "profiles": 412},
                "bay_of_bengal": {"avg": 33.9, "profiles": 480}
            }
        }
    },
    "float": {
        "message": "Found 47 ARGO floats in the specified region:\n\n🎯 Active floats: 42\n📡 Last transmission: 2 hours ago\n🗺️ Geographic distribution: Indian Ocean\n📈 Total profiles: 23,847\n\n*Floats are well-distributed across major ocean basins with good temporal coverage.*",
        "sql_query": """
SELECT 
    float_id,
    COUNT(*) as profile_count,
    MIN(measurement_date) as first_profile,
    MAX(measurement_date) as latest_profile,
    AVG(latitude) as avg_lat,
    AVG(longitude) as avg_lon
FROM argo_profiles 
GROUP BY float_id
ORDER BY latest_profile DESC
LIMIT 50;
        """.strip(),
        "data": {
            "total_floats": 47,
            "active_floats": 42,
            "total_profiles": 23847,
            "coverage_area": "Indian Ocean",
            "active_floats_list": [
                {"float_id": "2902755", "status": "active", "last_transmission": "2h ago", "profiles": 1247},
                {"float_id": "2902756", "status": "active", "last_transmission": "4h ago", "profiles": 1156},
                {"float_id": "2902758", "status": "active", "last_transmission": "6h ago", "profiles": 891}
            ]
        }
    }
}


@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """
    Process a natural language query about ocean data.
    
    This endpoint converts natural language questions into SQL queries,
    executes them against the ARGO database, and returns formatted results.
    """
    import time
    start_time = time.time()
    
    # Generate conversation ID if not provided
    conversation_id = request.conversation_id or f"conv_{int(time.time())}"
    
    # Simple keyword-based routing for demo
    query_lower = request.message.lower()
    
    if "temperature" in query_lower:
        response_data = MOCK_RESPONSES["temperature"]
    elif "salinity" in query_lower:
        response_data = MOCK_RESPONSES["salinity"]
    elif "float" in query_lower:
        response_data = MOCK_RESPONSES["float"]
    else:
        response_data = {
            "message": "I understand you're asking about ocean data. I can help you explore:\n\n🌡️ **Temperature profiles** - Ask about temperature trends, thermoclines, seasonal variations\n🧂 **Salinity data** - Explore salinity patterns, water masses, freshwater influences\n🛟 **Float information** - Get details on ARGO float locations, status, and coverage\n📊 **Data analysis** - Statistical summaries, anomaly detection, regional comparisons\n\nCould you be more specific about what ocean data you'd like to analyze?",
            "sql_query": None,
            "data": {
                "suggestions": [
                    "Show me temperature profiles in the Arabian Sea",
                    "What's the average salinity in the Bay of Bengal?",
                    "How many active floats are there near the Maldives?",
                    "Find temperature anomalies in March 2023"
                ]
            }
        }
    
    processing_time = (time.time() - start_time) * 1000
    
    return ChatResponse(
        message=response_data["message"],
        sql_query=response_data.get("sql_query") if request.include_sql else None,
        data=response_data.get("data"),
        conversation_id=conversation_id,
        processing_time_ms=processing_time
    )


@router.get("/conversations", response_model=List[ConversationHistory])
async def get_conversations():
    """Get user's conversation history."""
    # Mock conversation history for demo
    return [
        ConversationHistory(
            conversation_id="conv_1699123456",
            messages=[
                ChatMessage(role="user", content="Show me temperature data near India"),
                ChatMessage(role="assistant", content="I found 1,247 temperature profiles...")
            ],
            created_at=datetime(2023, 11, 1, 10, 30),
            updated_at=datetime(2023, 11, 1, 10, 35)
        )
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """Get specific conversation details."""
    # Mock conversation for demo
    return ConversationHistory(
        conversation_id=conversation_id,
        messages=[
            ChatMessage(role="user", content="Show me temperature profiles near 10°N"),
            ChatMessage(role="assistant", content="I found temperature data for your query...")
        ],
        created_at=datetime(2023, 11, 1, 10, 30),
        updated_at=datetime(2023, 11, 1, 10, 35)
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    return {"message": f"Conversation {conversation_id} deleted successfully"}


@router.post("/feedback")
async def submit_feedback(
    conversation_id: str,
    message_id: str,
    rating: int = Field(..., ge=1, le=5),
    comment: Optional[str] = None
):
    """Submit feedback on AI responses."""
    return {
        "message": "Feedback submitted successfully",
        "conversation_id": conversation_id,
        "rating": rating
    }
