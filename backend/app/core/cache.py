import redis
import json
import hashlib
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ResumeCache:
    def __init__(self):
        """Initialize Redis connection and cache settings"""
        try:
            # Codespaces Redis connection
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                db=0, 
                decode_responses=True,
                socket_connect_timeout=3
            )
            self.redis_client.ping() #Test connection
            self.enabled = True
            self.DEFAULT_JOB_TITLE = "not_specified"
            self.DEFAULT_JOB_DESC = "not_specified"
            logger.info("✅ Redis cache enabled")
        except Exception as e:
            self.enabled = False
            logger.warning(f"❌ Redis disabled: {e}")

    def _get_resume_fingerprint(self, resume_text: str) -> str:
        """Create a unique fingerprint of the resume content"""
        normalized = resume_text.lower().strip()
        normalized = ' '.join(normalized.split())  # Remove extra whitespace
        return hashlib.md5(normalized.encode()).hexdigest()

    def _normalize_job_fields(self, job_title: str = None, job_desc: str = None) -> tuple:
        """Normalize optional job fields to consistent values"""
        job_title = job_title.strip() if job_title and job_title.strip() else self.DEFAULT_JOB_TITLE
        job_desc = job_desc.strip() if job_desc and job_desc.strip() else self.DEFAULT_JOB_DESC
        return job_title, job_desc

    def get_cached_analysis(self, user_id: str, resume_text: str, job_desc: str = None, job_title: str = None) -> Optional[dict]:
        """Get cached analysis with user_id and optional job fields"""
        if not self.enabled:
            return None
            
        try:
            # Normalize optional fields
            job_title, job_desc = self._normalize_job_fields(job_title, job_desc)
            
            # Generate cache key with user_id
            resume_fingerprint = self._get_resume_fingerprint(resume_text)
            job_fingerprint = hashlib.md5(f"{job_title}_{job_desc}".encode()).hexdigest()
            cache_key = f"analysis:{user_id}:{resume_fingerprint}:{job_fingerprint}"
            
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info(f"🎯 Cache HIT for user {user_id}")
                return json.loads(cached)
                
            logger.info(f"💥 Cache MISS for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set_cached_analysis(self, user_id: str, resume_text: str, job_desc: str = None, job_title: str = None, analysis_result: dict = None, ttl: int = 86400):
        """Cache analysis result with user_id and optional job fields"""
        if not self.enabled or not analysis_result:
            return
            
        try:
            # Normalize optional fields
            job_title, job_desc = self._normalize_job_fields(job_title, job_desc)
            
            # Generate cache key with user_id
            resume_fingerprint = self._get_resume_fingerprint(resume_text)
            job_fingerprint = hashlib.md5(f"{job_title}_{job_desc}".encode()).hexdigest()
            cache_key = f"analysis:{user_id}:{resume_fingerprint}:{job_fingerprint}"
            
            # Store the analysis
            self.redis_client.setex(cache_key, ttl, json.dumps(analysis_result))
            
            # Track user-resume relationship for easy invalidation
            user_resumes_key = f"user_resumes:{user_id}"
            self.redis_client.sadd(user_resumes_key, resume_fingerprint)
            
            logger.info(f"💾 Cached analysis for user {user_id}")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def invalidate_user_resumes(self, user_id: str):
        """Clear ALL cached analyses for a user"""
        if not self.enabled:
            return
            
        try:
            user_resumes_key = f"user_resumes:{user_id}"
            resume_fingerprints = self.redis_client.smembers(user_resumes_key)
            
            # Delete all analysis cache entries for this user
            for fingerprint in resume_fingerprints:
                pattern = f"analysis:{user_id}:{fingerprint}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            # Clear the user's resume set
            self.redis_client.delete(user_resumes_key)
            logger.info(f"🗑️ Cleared all cached analyses for user {user_id}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

# Global cache instance
resume_cache = ResumeCache()