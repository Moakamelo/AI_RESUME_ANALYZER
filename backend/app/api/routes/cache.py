from fastapi import APIRouter, Depends, HTTPException, status
from app.core.cache import resume_cache
from app.api.dependencies import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/status")
async def get_cache_status():
    """Get global cache status (public - safe for monitoring)"""
    if not resume_cache.enabled:
        return {"cache_enabled": False}
    
    try:
        # Count all cached analyses
        analysis_keys = resume_cache.redis_client.keys("analysis:*")
        
        # Count by user (for statistics only)
        user_stats = {}
        for key in analysis_keys:
            parts = key.split(":")
            if len(parts) >= 2:
                user_id = parts[1] if len(parts) > 2 else "shared"
                user_stats[user_id] = user_stats.get(user_id, 0) + 1
        
        return {
            "cache_enabled": True,
            "total_cached_analyses": len(analysis_keys),
            "users_with_cached_data": len(user_stats),
            "cache_statistics": user_stats
        }
    except Exception as e:
        return {"cache_enabled": True, "error": str(e)}


@router.delete("/clear-my-cache")
async def clear_my_cache(current_user: User = Depends(get_current_user)):
    """Clear only current user's cache"""
    if not resume_cache.enabled:
        return {"message": "Cache is not enabled"}
    
    try:
        user_id = str(current_user.id)
        keys_before = resume_cache.redis_client.keys(f"analysis:{user_id}:*")
        user_resumes_key = f"user_resumes:{user_id}"
        
        # Delete user's analysis cache
        if keys_before:
            resume_cache.redis_client.delete(*keys_before)
        
        # Delete user's resume tracking
        resume_cache.redis_client.delete(user_resumes_key)
        
        logger.info(f"User cache cleared: {current_user.username}, {len(keys_before)} analyses removed")
        
        return {
            "message": f"Your cache has been cleared. {len(keys_before)} analyses removed.",
            "user_id": user_id,
            "analyses_cleared": len(keys_before)
        }
        
    except Exception as e:
        logger.error(f"User cache clearance failed for {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear your cache: {str(e)}"
        )