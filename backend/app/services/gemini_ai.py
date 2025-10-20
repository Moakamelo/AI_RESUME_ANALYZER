import os
import asyncio
from google import genai
from typing import Dict, Optional
import json
import logging
from app.core.performance import timer
from app.core.cache import resume_cache  
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class GeminiAIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=api_key)
        logger.info("✅ Gemini AI client initialized")
        
        self.model = "gemini-2.0-flash-exp"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    @timer("gemini_api_call")
    async def analyze_resume_ats(self, extracted_text: str, job_title: Optional[str] = None, job_description: Optional[str] = None, user_id: str = "anonymous") -> Dict:
        """ATS-focused resume analysis with caching and retry logic"""
        
        # 1. Check cache first
        cached_result = resume_cache.get_cached_analysis(
            user_id=user_id,
            resume_text=extracted_text,
            job_desc=job_description,
            job_title=job_title
        )
        
        if cached_result:
            logger.info("🎯 Serving cached analysis result")
            cached_result["source"] = "cache"
            return cached_result
        
        # 2. If not cached, call Gemini API
        try:
            logger.info("🤖 Starting ATS resume analysis (cache miss)...")
            
            async with asyncio.timeout(30):
                prompt = self._build_ats_analysis_prompt(extracted_text, job_title, job_description)
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                
                analysis_result = self._parse_ai_response(response.text)
                
                # 3. Cache successful results
                if not analysis_result.get('analysis_error'):
                    resume_cache.set_cached_analysis(
                        user_id=user_id,
                        resume_text=extracted_text,
                        job_desc=job_description,
                        job_title=job_title,
                        analysis_result=analysis_result
                    )
                    analysis_result["source"] = "api"
                else:
                    analysis_result["source"] = "api_error"
                
                logger.info("✅ ATS resume analysis completed successfully")
                return analysis_result
            
        except asyncio.TimeoutError:
            logger.error("❌ Gemini API request timed out after 30 seconds")
            error_result = self._get_fallback_analysis("Request timeout")
            error_result["source"] = "timeout"
            return error_result
        except Exception as e:
            logger.error(f"❌ Gemini AI ATS analysis error: {str(e)}")
            error_result = self._get_fallback_analysis(str(e))
            error_result["source"] = "error"
            return error_result

    def _build_ats_analysis_prompt(self, resume_text: str, job_title: Optional[str] = None, job_description: Optional[str] = None) -> str:
        """Build ATS-focused resume analysis prompt using the new format"""
        
        clean_resume_text = resume_text.strip()[:10000]
        clean_job_desc = (job_description or "").strip()[:3000]
        
        prompt = f"""
You are an expert in ATS (Applicant Tracking System) and resume analysis.
Please analyze and rate this resume and suggest how to improve it.
The rating can be low if the resume is bad.
Be thorough and detailed. Don't be afraid to point out any mistakes or areas for improvement.
If there is a lot to improve, don't hesitate to give low scores. This is to help the user to improve their resume.
If available, use the job description for the job user is applying to to give more detailed feedback.
If provided, take the job description into consideration.

JOB TITLE: {job_title or "Not specified"}
JOB DESCRIPTION: {clean_job_desc or "Not provided"}

RESUME CONTENT:
{clean_resume_text}

Provide the feedback using the following EXACT JSON format:
{{
  "overallScore": 75,
  "ATS": {{
    "score": 70,
    "tips": [
      {{
        "type": "good",
        "tip": "Clear section headings"
      }},
      {{
        "type": "improve", 
        "tip": "Add more keywords from job description"
      }},
      {{
        "type": "improve",
        "tip": "Improve formatting for ATS"
      }}
    ]
  }},
  "toneAndStyle": {{
    "score": 80,
    "tips": [
      {{
        "type": "good",
        "tip": "Professional tone",
        "explanation": "The resume maintains a professional tone throughout"
      }},
      {{
        "type": "improve",
        "tip": "Use more action verbs", 
        "explanation": "Incorporate more action verbs to make achievements stand out"
      }},
      {{
        "type": "improve",
        "tip": "Quantify achievements",
        "explanation": "Add specific numbers and metrics to demonstrate impact"
      }}
    ]
  }},
  "content": {{
    "score": 75,
    "tips": [
      {{
        "type": "good",
        "tip": "Relevant work experience",
        "explanation": "Work experience is relevant to the target role"
      }},
      {{
        "type": "improve",
        "tip": "Add quantifiable achievements",
        "explanation": "Include specific numbers and metrics to demonstrate impact"
      }},
      {{
        "type": "improve",
        "tip": "Tailor to job description",
        "explanation": "Customize content to match the specific job requirements"
      }}
    ]
  }},
  "structure": {{
    "score": 70,
    "tips": [
      {{
        "type": "good",
        "tip": "Clear chronological order",
        "explanation": "Work experience is presented in clear reverse chronological order"
      }},
      {{
        "type": "improve",
        "tip": "Improve spacing",
        "explanation": "Some sections are too dense and could benefit from better spacing"
      }},
      {{
        "type": "improve",
        "tip": "Consistent formatting",
        "explanation": "Ensure consistent formatting throughout the document"
      }}
    ]
  }},
  "skills": {{
    "score": 85,
    "tips": [
      {{
        "type": "good",
        "tip": "SQL programming",
        "explanation": "SQL skills are clearly demonstrated in project experience"
      }},
      {{
        "type": "good",
        "tip": "Python development",
        "explanation": "Python programming experience is well-documented"
      }},
      {{
        "type": "improve",
        "tip": "Power BI visualization",
        "explanation": "Add experience with data visualization tools like Power BI"
      }},
      {{
        "type": "improve",
        "tip": "Advanced Excel skills",
        "explanation": "Include specific Advanced Excel capabilities relevant to the role"
      }}
    ]
  }}
}}

CRITICAL INSTRUCTIONS:
- Return ONLY the JSON object, no other text
- Do not include markdown formatting or code blocks
- Ensure all scores are integers between 0-100
- For skills tips, be VERY specific about actual technical skills (e.g., "Python", "SQL", "Power BI", not generic terms)
- Provide 3-4 tips for each category
- Be honest and critical - low scores help users improve
- Focus on actionable, specific feedback
"""

        return prompt

    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse the AI response and extract JSON"""
        try:
            if not response_text:
                logger.error("❌ Empty response from AI")
                return self._get_fallback_analysis("Empty response")
            
            cleaned_text = response_text.strip()
            logger.info(f"📄 Raw AI response length: {len(cleaned_text)}")
            
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = cleaned_text[start_idx:end_idx]
                logger.info(f"📄 Extracted JSON: {json_str[:200]}...")
                
                result = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['overallScore', 'ATS', 'toneAndStyle', 'content', 'structure', 'skills']
                for field in required_fields:
                    if field not in result:
                        logger.warning(f"⚠️ Missing field in AI response: {field}")
                        result[field] = self._get_fallback_analysis().get(field, {})
                
                return result
            else:
                logger.error("❌ No JSON structure found in AI response")
                return self._get_fallback_analysis("No JSON structure found")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            return self._get_fallback_analysis(f"JSON parsing error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected parsing error: {e}")
            return self._get_fallback_analysis(f"Unexpected error: {e}")

    def _get_fallback_analysis(self, error_message: str = "Unknown error") -> Dict:
        """Return comprehensive fallback analysis when AI fails"""
        return {
            "overallScore": 50,
            "ATS": {
                "score": 50,
                "tips": [
                    {
                        "type": "improve",
                        "tip": "AI analysis temporarily unavailable"
                    }
                ]
            },
            "toneAndStyle": {
                "score": 50,
                "tips": [
                    {
                        "type": "improve",
                        "tip": "Analysis pending",
                        "explanation": "AI service is currently unavailable. Please try again later."
                    }
                ]
            },
            "content": {
                "score": 50,
                "tips": [
                    {
                        "type": "improve",
                        "tip": "Analysis pending",
                        "explanation": "AI service is currently unavailable. Please try again later."
                    }
                ]
            },
            "structure": {
                "score": 50,
                "tips": [
                    {
                        "type": "improve",
                        "tip": "Analysis pending",
                        "explanation": "AI service is currently unavailable. Please try again later."
                    }
                ]
            },
            "skills": {
                "score": 50,
                "tips": [
                    {
                        "type": "improve",
                        "tip": "Analysis pending",
                        "explanation": "AI service is currently unavailable. Please try again later."
                    }
                ]
            },
            "analysis_error": True,
            "error_message": error_message
        }

    @timer("gemini_health_check")
    async def check_api_health(self) -> Dict:
        """Check if the Gemini API is working properly"""
        try:
            async with asyncio.timeout(10):
                response = self.client.models.generate_content(
                    model=self.model,
                    contents="Respond with exactly: OK"
                )
                
                if "ok" in response.text.lower():
                    return {
                        "status": "healthy", 
                        "message": "Gemini API is working correctly",
                        "model": self.model
                    }
                else:
                    return {
                        "status": "unhealthy", 
                        "message": "Unexpected API response",
                        "response": response.text[:100]
                    }
                    
        except asyncio.TimeoutError:
            return {
                "status": "error", 
                "message": "Health check timeout - API may be slow",
                "model": self.model
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"API health check failed: {str(e)}",
                "model": self.model
            }

try:
    gemini_ai_service = GeminiAIService()
    logger.info("🎯 Gemini AI service ready with caching integration")
except Exception as e:
    logger.error(f"💥 Gemini AI service failed to initialize: {e}")
    
    class FallbackAIService:
        async def analyze_resume_ats(self, *args, **kwargs):
            result = self._get_fallback_analysis("Service initialization failed")
            result["source"] = "fallback"
            return result
            
        async def check_api_health(self):
            return {"status": "error", "message": "Service not initialized"}
            
        def _get_fallback_analysis(self, error_message: str) -> Dict:
            return {
                "overallScore": 50,
                "ATS": {"score": 50, "tips": [{"type": "improve", "tip": "Service unavailable"}]},
                "toneAndStyle": {"score": 50, "tips": [{"type": "improve", "tip": "Service unavailable", "explanation": "AI service initialization failed"}]},
                "content": {"score": 50, "tips": [{"type": "improve", "tip": "Service unavailable", "explanation": "AI service initialization failed"}]},
                "structure": {"score": 50, "tips": [{"type": "improve", "tip": "Service unavailable", "explanation": "AI service initialization failed"}]},
                "skills": {"score": 50, "tips": [{"type": "improve", "tip": "Service unavailable", "explanation": "AI service initialization failed"}]},
                "analysis_error": True
            }
    
    gemini_ai_service = FallbackAIService()