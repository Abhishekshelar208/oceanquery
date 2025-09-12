"""
Enhanced Chat API endpoints with RAG support.

Provides intelligent, context-aware chat functionality for oceanographic queries.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import dependencies
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core.config import settings
from services.nlp.enhanced_chat_pipeline import create_enhanced_chat_pipeline
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Global pipeline instance (initialized on first use)
_pipeline = None


def get_pipeline():
    """Get or create the enhanced chat pipeline instance."""
    global _pipeline
    if _pipeline is None:
        try:
            _pipeline = create_enhanced_chat_pipeline(enable_rag=True)
            logger.info("Enhanced chat pipeline with RAG initialized")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced chat pipeline: {e}")
            # Fallback without RAG
            _pipeline = create_enhanced_chat_pipeline(enable_rag=False)
            logger.warning("Enhanced chat pipeline initialized without RAG support")
    return _pipeline


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., description="User's natural language query", min_length=1, max_length=1000)
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")
    include_sql: bool = Field(True, description="Include generated SQL in response")
    max_results: int = Field(100, description="Maximum number of results to return", ge=1, le=1000)
    enable_rag: bool = Field(True, description="Enable RAG enhancements")


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str = Field(..., description="AI-generated response message")
    sql_query: Optional[str] = Field(None, description="Generated SQL query (if requested)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Query results and metadata")
    visualizations: list = Field(default_factory=list, description="Suggested visualizations")
    suggestions: list = Field(default_factory=list, description="Follow-up query suggestions")
    context_info: Dict[str, Any] = Field(default_factory=dict, description="Query context information")
    conversation_id: str = Field(..., description="Conversation ID")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    success: bool = Field(..., description="Whether the query was successful")


class PipelineStatsResponse(BaseModel):
    """Pipeline statistics response model."""
    total_queries_processed: int
    successful_queries: int
    failed_queries: int
    success_rate: float
    average_processing_time_ms: float
    average_confidence: float
    rag_enabled: bool
    rag_enhanced_queries: int
    rag_enhancement_rate: float
    total_knowledge_chunks_used: int
    avg_knowledge_chunks_per_query: float
    conversation_stats: Dict[str, Any]
    rag_system_stats: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def enhanced_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Process natural language query with enhanced AI chat pipeline.
    
    This endpoint provides intelligent, context-aware responses to oceanographic
    queries with optional RAG (Retrieval-Augmented Generation) enhancements.
    """
    try:
        # Get pipeline instance
        pipeline = get_pipeline()
        
        # Temporarily disable RAG if requested
        if not request.enable_rag and hasattr(pipeline, 'enable_rag'):
            original_rag_setting = pipeline.enable_rag
            pipeline.enable_rag = False
        else:
            original_rag_setting = None
        
        # Process the query
        result = await pipeline.process_query(
            user_query=request.query,
            conversation_id=request.conversation_id,
            include_sql=request.include_sql,
            max_results=request.max_results,
            db_session=db
        )
        
        # Restore RAG setting if it was changed
        if original_rag_setting is not None:
            pipeline.enable_rag = original_rag_setting
        
        # Convert to response model
        response = ChatResponse(
            message=result.get('message', ''),
            sql_query=result.get('sql_query'),
            data=result.get('data', {}),
            visualizations=result.get('visualizations', []),
            suggestions=result.get('suggestions', []),
            context_info=result.get('context_info', {}),
            conversation_id=result.get('conversation_id', ''),
            processing_time_ms=result.get('processing_time_ms', 0.0),
            success=result.get('success', False)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


@router.get("/chat/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats():
    """
    Get enhanced chat pipeline statistics.
    
    Returns performance metrics including RAG enhancement statistics.
    """
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_pipeline_stats()
        
        return PipelineStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pipeline statistics: {str(e)}"
        )


@router.post("/chat/reset-conversation")
async def reset_conversation(conversation_id: str):
    """Reset/clear a specific conversation context."""
    
    try:
        pipeline = get_pipeline()
        
        # Clear conversation context if the pipeline has conversation manager
        if hasattr(pipeline, 'conversation_manager'):
            if conversation_id in pipeline.conversation_manager.contexts:
                del pipeline.conversation_manager.contexts[conversation_id]
                return {"message": f"Conversation {conversation_id} reset successfully"}
            else:
                return {"message": f"Conversation {conversation_id} not found"}
        else:
            return {"message": "Conversation management not available"}
            
    except Exception as e:
        logger.error(f"Conversation reset error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset conversation: {str(e)}"
        )


@router.get("/chat/knowledge-stats")
async def get_knowledge_stats():
    """
    Get RAG knowledge base statistics.
    
    Returns information about the loaded knowledge collections.
    """
    try:
        pipeline = get_pipeline()
        
        if not pipeline.enable_rag or not pipeline.rag_system:
            return {
                "rag_enabled": False,
                "message": "RAG system not available"
            }
        
        # Get knowledge manager stats
        if hasattr(pipeline, 'knowledge_manager'):
            knowledge_stats = pipeline.knowledge_manager.get_knowledge_stats()
            return {
                "rag_enabled": True,
                "knowledge_stats": knowledge_stats
            }
        else:
            return {
                "rag_enabled": True,
                "message": "Knowledge manager not accessible"
            }
            
    except Exception as e:
        logger.error(f"Knowledge stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve knowledge statistics: {str(e)}"
        )


@router.post("/chat/reload-knowledge")
async def reload_knowledge(background_tasks: BackgroundTasks):
    """
    Reload the RAG knowledge base.
    
    This will refresh the vector database with the latest oceanographic knowledge.
    """
    try:
        pipeline = get_pipeline()
        
        if not pipeline.enable_rag or not hasattr(pipeline, 'knowledge_manager'):
            raise HTTPException(
                status_code=400,
                detail="RAG system not available or knowledge manager not accessible"
            )
        
        def reload_task():
            """Background task to reload knowledge."""
            try:
                load_results = pipeline.knowledge_manager.load_oceanographic_knowledge()
                successful_loads = sum(1 for success in load_results.values() if success)
                logger.info(f"Knowledge reloaded: {successful_loads}/{len(load_results)} collections")
            except Exception as e:
                logger.error(f"Knowledge reload failed: {e}")
        
        # Run reload in background
        background_tasks.add_task(reload_task)
        
        return {
            "message": "Knowledge reload initiated in background",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Knowledge reload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate knowledge reload: {str(e)}"
        )


@router.get("/chat/health")
async def health_check():
    """
    Health check for the enhanced chat system.
    
    Returns system status and component availability.
    """
    try:
        pipeline = get_pipeline()
        
        # Check components
        health_status = {
            "status": "healthy",
            "components": {
                "pipeline": "available",
                "query_parser": "available" if hasattr(pipeline, 'query_parser') else "unavailable",
                "sql_generator": "available" if hasattr(pipeline, 'sql_generator') else "unavailable", 
                "conversation_manager": "available" if hasattr(pipeline, 'conversation_manager') else "unavailable",
                "rag_system": "available" if (pipeline.enable_rag and pipeline.rag_system) else "unavailable"
            },
            "rag_enabled": pipeline.enable_rag,
            "configuration": {
                "auto_load_knowledge": settings.auto_load_knowledge,
                "rag_max_context_tokens": settings.rag_max_context_tokens,
                "rag_relevance_threshold": settings.rag_relevance_threshold,
                "rag_max_chunks": settings.rag_max_chunks
            }
        }
        
        # Add knowledge base info if available
        if pipeline.enable_rag and hasattr(pipeline, 'knowledge_manager'):
            try:
                kb_stats = pipeline.knowledge_manager.get_knowledge_stats()
                health_status["knowledge_base"] = {
                    "total_documents": kb_stats.get('total_documents', 0),
                    "collections": len(kb_stats.get('collections', {})),
                    "loaded_sources": kb_stats.get('loaded_sources', [])
                }
            except Exception as e:
                health_status["knowledge_base"] = {"error": str(e)}
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }