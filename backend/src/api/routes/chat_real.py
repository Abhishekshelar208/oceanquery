"""
Enhanced Chat API routes with real ARGO data integration.
"""

import time
from typing import List, Optional
from datetime import datetime
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# Import database dependencies
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.config import settings
from db.models import ArgoFloat, ArgoProfile, ArgoMeasurement
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import enhanced chat pipeline
try:
    from services.nlp.enhanced_chat_pipeline import create_enhanced_chat_pipeline
    ENHANCED_PIPELINE_AVAILABLE = True
except ImportError:
    ENHANCED_PIPELINE_AVAILABLE = False
    print("Enhanced chat pipeline not available - using basic version")

router = APIRouter()

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize enhanced chat pipeline if available
if ENHANCED_PIPELINE_AVAILABLE:
    chat_pipeline = create_enhanced_chat_pipeline(db_session_factory=SessionLocal)
else:
    chat_pipeline = None

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

def analyze_real_measurement_data(db: Session, parameter: str = "temperature"):
    """Analyze real measurement data from the database."""
    # Get measurement statistics
    total_measurements = db.query(ArgoMeasurement).count()
    profiles_with_measurements = db.query(func.count(func.distinct(ArgoMeasurement.profile_id))).scalar()
    
    if total_measurements == 0:
        return {
            "message": "❌ No measurement data found in the database. Please check data ingestion.",
            "sql_query": "SELECT COUNT(*) FROM argo_measurements;",
            "data": {"error": "No measurements found"}
        }
    
    # Get parameter-specific statistics
    param_column = getattr(ArgoMeasurement, parameter, None)
    if not param_column:
        return {
            "message": f"❌ Parameter '{parameter}' not available.",
            "sql_query": None,
            "data": {"error": f"Invalid parameter: {parameter}"}
        }
    
    # Parameter statistics
    param_stats = db.query(
        func.count(param_column).label('count'),
        func.avg(param_column).label('mean'),
        func.min(param_column).label('min'),
        func.max(param_column).label('max')
    ).filter(param_column.isnot(None)).first()
    
    # Depth range
    depth_stats = db.query(
        func.min(ArgoMeasurement.depth).label('min_depth'),
        func.max(ArgoMeasurement.depth).label('max_depth')
    ).filter(ArgoMeasurement.depth.isnot(None)).first()
    
    # Get a profile with good data for plotting
    sample_profile = db.query(ArgoProfile).join(ArgoMeasurement).filter(
        param_column.isnot(None)
    ).first()
    
    # Format parameter name for display
    param_names = {
        'temperature': '🌡️ Temperature',
        'salinity': '🧂 Salinity', 
        'oxygen': '💨 Oxygen',
        'pressure': '🔵 Pressure'
    }
    param_display = param_names.get(parameter, parameter.title())
    
    # Units
    param_units = {
        'temperature': '°C',
        'salinity': 'PSU',
        'oxygen': 'μmol/kg',
        'pressure': 'dbar'
    }
    unit = param_units.get(parameter, '')
    
    message = f"🌊 **Real ARGO {param_display} Data Analysis**\\n\\n"
    message += f"📊 **Measurements**: {total_measurements:,} total\\n"
    message += f"📂 **Profiles**: {profiles_with_measurements:,} with {parameter} data\\n"
    
    if param_stats and param_stats.count > 0:
        message += f"📈 **{param_display} Range**: {param_stats.min:.2f} to {param_stats.max:.2f} {unit}\\n"
        message += f"📊 **Average {parameter.title()}**: {param_stats.mean:.2f} {unit}\\n"
    
    if depth_stats:
        message += f"🌊 **Depth Range**: {depth_stats.min_depth:.0f}m to {depth_stats.max_depth:.0f}m\\n"
    
    if sample_profile:
        message += f"\\n💡 **Try asking**: \"Show me a {parameter} profile for {sample_profile.profile_id}\"\\n"
    
    message += f"\\n*This is real oceanographic data from ARGO floats!*"
    
    return {
        "message": message,
        "sql_query": f'''
SELECT 
    COUNT(*) as total_measurements,
    COUNT(DISTINCT profile_id) as profiles_count,
    AVG({parameter}) as avg_{parameter},
    MIN({parameter}) as min_{parameter},
    MAX({parameter}) as max_{parameter}
FROM argo_measurements 
WHERE {parameter} IS NOT NULL;
        '''.strip(),
        "data": {
            "total_measurements": total_measurements,
            "profiles_with_measurements": profiles_with_measurements,
            "parameter": parameter,
            "parameter_stats": {
                "count": param_stats.count if param_stats else 0,
                "mean": float(param_stats.mean) if param_stats and param_stats.mean else None,
                "min": float(param_stats.min) if param_stats and param_stats.min else None,
                "max": float(param_stats.max) if param_stats and param_stats.max else None,
                "unit": unit
            },
            "depth_range": {
                "min_depth": float(depth_stats.min_depth) if depth_stats and depth_stats.min_depth else None,
                "max_depth": float(depth_stats.max_depth) if depth_stats and depth_stats.max_depth else None
            },
            "sample_profile_id": sample_profile.profile_id if sample_profile else None
        }
    }

def analyze_specific_profile(db: Session, profile_id: str, parameter: str = "temperature"):
    """Analyze a specific profile and generate plot if requested."""
    # Get profile
    profile = db.query(ArgoProfile).filter(ArgoProfile.profile_id == profile_id).first()
    if not profile:
        return {
            "message": f"❌ Profile {profile_id} not found.",
            "sql_query": f"SELECT * FROM argo_profiles WHERE profile_id = '{profile_id}';",
            "data": {"error": "Profile not found"}
        }
    
    # Get measurements for this profile
    measurements = db.query(ArgoMeasurement).filter(
        ArgoMeasurement.profile_id == profile_id
    ).order_by(ArgoMeasurement.pressure).all()
    
    if not measurements:
        return {
            "message": f"❌ No measurements found for profile {profile_id}.",
            "sql_query": f"SELECT * FROM argo_measurements WHERE profile_id = '{profile_id}';",
            "data": {"error": "No measurements found"}
        }
    
    # Extract parameter data
    param_data = []
    depths = []
    for m in measurements:
        value = getattr(m, parameter, None)
        if value is not None and m.depth is not None:
            param_data.append(float(value))
            depths.append(float(m.depth))
    
    if not param_data:
        return {
            "message": f"❌ No {parameter} data found for profile {profile_id}.",
            "sql_query": f"SELECT {parameter}, depth FROM argo_measurements WHERE profile_id = '{profile_id}' AND {parameter} IS NOT NULL;",
            "data": {"error": f"No {parameter} data"}
        }
    
    # Calculate statistics
    import numpy as np
    mean_val = np.mean(param_data)
    min_val = np.min(param_data)
    max_val = np.max(param_data)
    depth_range = (np.min(depths), np.max(depths))
    
    # Parameter units
    param_units = {
        'temperature': '°C',
        'salinity': 'PSU', 
        'oxygen': 'μmol/kg',
        'pressure': 'dbar'
    }
    unit = param_units.get(parameter, '')
    
    message = f"🌊 **Profile {profile_id} Analysis**\\n\\n"
    message += f"📍 **Location**: {profile.latitude:.2f}°N, {profile.longitude:.2f}°E\\n"
    message += f"📅 **Date**: {profile.measurement_date.strftime('%Y-%m-%d')}\\n"
    message += f"🛟 **Float**: {profile.float_id}\\n\\n"
    message += f"📊 **{parameter.title()} Statistics**:\\n"
    message += f"  • Range: {min_val:.2f} to {max_val:.2f} {unit}\\n"
    message += f"  • Average: {mean_val:.2f} {unit}\\n"
    message += f"  • Depth: {depth_range[0]:.0f}m to {depth_range[1]:.0f}m\\n"
    message += f"  • Measurements: {len(param_data)}\\n\\n"
    
    # Suggest visualization
    message += f"💡 **Visualization available**: Ask me to \"plot {parameter} for {profile_id}\" to see a depth profile!"
    
    return {
        "message": message,
        "sql_query": f'''
SELECT 
    pressure, depth, {parameter},
    {parameter}_qc as quality_flag
FROM argo_measurements 
WHERE profile_id = '{profile_id}'
  AND {parameter} IS NOT NULL
ORDER BY pressure;
        '''.strip(),
        "data": {
            "profile_id": profile_id,
            "float_id": profile.float_id,
            "location": {
                "latitude": profile.latitude,
                "longitude": profile.longitude
            },
            "measurement_date": profile.measurement_date.isoformat(),
            "parameter": parameter,
            "statistics": {
                "count": len(param_data),
                "mean": float(mean_val),
                "min": float(min_val),
                "max": float(max_val),
                "unit": unit
            },
            "depth_range": {
                "min_depth": depth_range[0],
                "max_depth": depth_range[1]
            },
            "plot_suggestion": f"plot {parameter} for {profile_id}"
        }
    }

def detect_query_intent(query: str):
    """Detect the user's intent from their query."""
    query_lower = query.lower().strip()
    
    # Patterns for simple count requests
    simple_count_patterns = [
        r'how many floats?',
        r'how many floats do you have?',
        r'floats count',
        r'^count floats?$',
        r'^\d+$',  # Just asking for a number
    ]
    
    # Check for simple count patterns
    import re
    for pattern in simple_count_patterns:
        if re.search(pattern, query_lower):
            return "simple_count"
    
    # Check if user asks specifically "how many" with float-related terms
    if ("how many" in query_lower and 
        any(term in query_lower for term in ["float", "sensor", "buoy", "device"]) and
        len(query_lower.split()) <= 8):  # Allow slightly longer queries like "how many active floats do you have"
        return "simple_count"
    
    # Otherwise, return detailed response
    return "detailed"

def analyze_real_float_data(db: Session, query: str = ""):
    """Analyze real float data from the database."""
    total_floats = db.query(ArgoFloat).count()
    active_floats = db.query(ArgoFloat).filter(ArgoFloat.status == 'active').count()
    total_profiles = db.query(ArgoProfile).count()
    
    # Detect user intent
    intent = detect_query_intent(query)
    
    if intent == "simple_count":
        # Return simple count response
        return {
            "message": str(total_floats),
            "sql_query": "SELECT COUNT(*) FROM argo_floats;",
            "data": {
                "total_floats": total_floats,
                "query_type": "simple_count"
            }
        }
    
    # Default detailed response
    # Get most active floats
    active_float_data = db.query(
        ArgoFloat.float_id,
        ArgoFloat.institution,
        ArgoFloat.total_profiles,
        ArgoFloat.last_latitude,
        ArgoFloat.last_longitude
    ).filter(ArgoFloat.status == 'active').limit(5).all()
    
    return {
        "message": f"Here's the real ARGO float data from our database:\\n\\n🛟 **Total Floats**: {total_floats}\\n✅ **Active Floats**: {active_floats}\\n📊 **Total Profiles**: {total_profiles:,}\\n🌊 **Coverage**: Global Ocean\\n\\n*These are real floating sensors collecting ocean data!*",
        "sql_query": '''
SELECT 
    float_id,
    institution,
    status,
    total_profiles,
    last_latitude,
    last_longitude,
    first_profile_date,
    last_profile_date
FROM argo_floats 
WHERE status = 'active'
ORDER BY total_profiles DESC
LIMIT 10;
        '''.strip(),
        "data": {
            "total_floats": total_floats,
            "active_floats": active_floats,
            "total_profiles": total_profiles,
            "active_float_sample": [
                {
                    "float_id": f.float_id,
                    "institution": f.institution or "Unknown",
                    "profiles": f.total_profiles or 0,
                    "position": {
                        "lat": float(f.last_latitude) if f.last_latitude else None,
                        "lon": float(f.last_longitude) if f.last_longitude else None
                    }
                }
                for f in active_float_data
            ]
        }
    }

def get_general_help():
    """Provide general help about ARGO data."""
    return {
        "message": "🌊 **Welcome to OceanQuery!** I can help you explore real ARGO oceanographic data.\\n\\n**What I can do:**\\n\\n🌡️ **Temperature Analysis**: *'Show me temperature data'*\\n🧂 **Salinity Patterns**: *'What's the salinity data?'*\\n🛟 **Float Information**: *'How many floats are active?'*\\n📊 **Data Statistics**: *'Give me a data summary'*\\n🗺️ **Geographic Queries**: *'Show data near coordinates'*\\n📅 **Temporal Analysis**: *'What data from 2020?'*\\n\\n**Try asking something like:**\\n• *'How many ARGO floats do we have?'*\\n• *'Show me data from the Atlantic Ocean'*\\n• *'What's the temperature range in our dataset?'*",
        "sql_query": None,
        "data": {
            "capabilities": [
                "Real ARGO float data analysis",
                "Temperature and salinity profiles",
                "Geographic and temporal filtering",
                "Statistical summaries",
                "Data quality assessment"
            ],
            "example_queries": [
                "How many ARGO floats are active?",
                "Show me temperature data",
                "What's the geographic coverage?",
                "Give me data statistics",
                "Show profiles from 2000-2005"
            ]
        }
    }

@router.post("/query", response_model=ChatResponse)
async def chat_query_real(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Process natural language queries with real ARGO data.
    """
    start_time = time.time()
    
    conversation_id = request.conversation_id or f"conv_{int(time.time())}"
    query_lower = request.message.lower()
    
    try:
        # Extract profile ID from query if present
        import re
        profile_match = re.search(r'\b(\d+_\d+)\b', request.message)
        
        # Check for plot requests
        plot_keywords = ["plot", "chart", "graph", "visualize", "show plot"]
        wants_plot = any(word in query_lower for word in plot_keywords)
        
        # Route queries based on content
        if profile_match:
            profile_id = profile_match.group(1)
            # Determine parameter from query
            if any(word in query_lower for word in ["temperature", "temp"]):
                parameter = "temperature"
            elif any(word in query_lower for word in ["salinity", "salt"]):
                parameter = "salinity" 
            elif any(word in query_lower for word in ["oxygen", "o2"]):
                parameter = "oxygen"
            elif any(word in query_lower for word in ["pressure"]):
                parameter = "pressure"
            else:
                parameter = "temperature"  # default
                
            if wants_plot:
                # Generate plot via measurement API endpoint
                response_data = {
                    "message": f"📊 Generating {parameter} plot for profile {profile_id}...\\n\\nPlot URL: `/api/v1/measurements/plot/{profile_id}?plot_type={parameter}`\\n\\nThis shows the depth profile of {parameter} measurements from ARGO float data!",
                    "sql_query": f"SELECT depth, {parameter} FROM argo_measurements WHERE profile_id = '{profile_id}' ORDER BY pressure;",
                    "data": {
                        "plot_url": f"/api/v1/measurements/plot/{profile_id}?plot_type={parameter}",
                        "profile_id": profile_id,
                        "parameter": parameter
                    }
                }
            else:
                response_data = analyze_specific_profile(db, profile_id, parameter)
                
        elif any(word in query_lower for word in ["temperature", "temp", "heat", "thermal"]):
            response_data = analyze_real_measurement_data(db, "temperature")
        elif any(word in query_lower for word in ["salinity", "salt", "psu"]):
            response_data = analyze_real_measurement_data(db, "salinity")
        elif any(word in query_lower for word in ["oxygen", "o2"]):
            response_data = analyze_real_measurement_data(db, "oxygen")
        elif any(word in query_lower for word in ["pressure"]):
            response_data = analyze_real_measurement_data(db, "pressure")
        elif any(word in query_lower for word in ["float", "sensor", "buoy", "device"]):
            response_data = analyze_real_float_data(db, request.message)
        elif any(word in query_lower for word in ["measurement", "data", "summary", "statistics", "stats"]):
            response_data = analyze_real_measurement_data(db, "temperature")
        else:
            response_data = get_general_help()
        
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            message=response_data["message"],
            sql_query=response_data.get("sql_query") if request.include_sql else None,
            data=response_data.get("data"),
            conversation_id=conversation_id,
            processing_time_ms=processing_time
        )
    
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return ChatResponse(
            message=f"I encountered an error while processing your query: {str(e)}\\n\\nPlease try rephrasing your question or ask for help.",
            sql_query=None,
            data={"error": str(e)},
            conversation_id=conversation_id,
            processing_time_ms=processing_time
        )


@router.post("/enhanced-query", response_model=ChatResponse)
async def chat_query_enhanced(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Process natural language queries using enhanced AI pipeline.
    """
    if not ENHANCED_PIPELINE_AVAILABLE or chat_pipeline is None:
        return ChatResponse(
            message="❌ Enhanced chat pipeline is not available. Please use the basic /query endpoint.",
            sql_query=None,
            data={"error": "Enhanced pipeline unavailable"},
            conversation_id=request.conversation_id or f"conv_{int(time.time())}",
            processing_time_ms=0.0
        )
    
    try:
        # Use the enhanced chat pipeline
        response = await chat_pipeline.process_query(
            user_query=request.message,
            conversation_id=request.conversation_id,
            include_sql=request.include_sql,
            max_results=request.max_results,
            db_session=db
        )
        
        # Convert to ChatResponse format
        return ChatResponse(
            message=response['message'],
            sql_query=response.get('sql_query'),
            data=response.get('data', {}),
            conversation_id=response['conversation_id'],
            processing_time_ms=response['processing_time_ms']
        )
        
    except Exception as e:
        return ChatResponse(
            message=f"I encountered an error while processing your query: {str(e)}\\n\\nPlease try rephrasing your question or ask for help.",
            sql_query=None,
            data={"error": str(e)},
            conversation_id=request.conversation_id or f"conv_{int(time.time())}",
            processing_time_ms=0.0
        )


@router.get("/pipeline-stats")
async def get_pipeline_statistics():
    """
    Get enhanced chat pipeline performance statistics.
    """
    if not ENHANCED_PIPELINE_AVAILABLE or chat_pipeline is None:
        return {"error": "Enhanced pipeline not available"}
    
    return chat_pipeline.get_pipeline_stats()
