# 🧠 AI Resume Analyzer — Technical Portfolio Project 🚀

*A high-performance, production-ready resume analysis platform built with modern Python and AI technologies.*

---

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-15%2B-336791?logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7.0%2B-DC382D?logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Supabase-Storage-3ECF8E?logo=supabase&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini%20AI-Integrated-4285F4?logo=google&logoColor=white" />
</p>

---

## 🎯 Project Overview

The **AI Resume Analyzer** is a **backend, AI-powered system** that provides instant, detailed feedback on resume **ATS (Applicant Tracking System)** compatibility.  
It leverages **Google’s Gemini AI** for intelligent scoring and improvement suggestions, designed for **speed, scalability, and compliance**.

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-------------|
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL (SQLAlchemy ORM) |
| **Caching** | Redis |
| **Storage** | Supabase |
| **AI Engine** | Google Gemini AI |
| **Authentication** | JWT |
| **Deployment** | Docker + CI/CD ready |

---

## 🧱 System Architecture Diagram
![Architecture Diagram](/documents/image.png)


## ⚡ Key Technical Achievements

### 🧩 Performance & Scalability
- **🚀 Smart Caching System**: Reduced API calls by **50%** and response times by **83%**
- **⚙️ Background Processing**: Async AI tasks for instant responses
- **📈 Metrics**: Real-time system performance tracking
- **🗄️ Optimized Database**: Connection pooling for high-concurrency operations

### 🤖 AI & Machine Learning
- **🔍 Gemini AI Integration**: ATS-based scoring and analysis
- **🧠 Prompt Engineering**: Consistent JSON-based structured outputs
- **⚡ Fallback Mode**: Handles AI downtime gracefully
- **📑 Multi-Category Scoring**: ATS, Content, Structure, Skills, Tone

### 🔒 Security & Compliance
- **✅ POPI Act Compliant**: South African data protection
- **🔐 JWT Authentication**: Secure token-based system
- **🧩 Encryption**: Data encryption at rest and in transit
- **📝 Consent Management**: User tracking and compliance logging

## 📊 Performance Metrics

| Metric | Before Optimization | After Optimization | Improvement |
|--------|---------------------|-------------------|-------------|
| First Analysis | 12.4s | 12.4s | - |
| Cached Analysis | 12.4s | **2.1s** | **83% faster** |
| API Calls | 2/request | **1/2 requests** | **50% reduction** |
| Cache Hit Rate | 0% | **50%+** | **Significant cost savings** |

<details>
<summary>🧾 Resume Management Features</summary>

### 📁 Resume Management
- PDF/DOCX upload and text extraction
- Smart caching for identical resume analyses
- Multi-version re-analysis for job-specific targeting
- Automatic PDF-to-image previews
- Signed URLs for secure downloads

</details>

<details>
<summary>👤 User Management</summary>

### 🔐 User Management
- JWT-based authentication with bcrypt password hashing
- POPI-compliant ID storage (SHA-256 + pepper)
- Consent management and right-to-be-forgotten support
- User profile and analysis history tracking

</details>

<details>
<summary>🩺 System Monitoring</summary>

### 📡 System Monitoring
- Full service health checks
- Redis cache hit/miss monitoring
- Real-time performance metrics
- Graceful error recovery and alerts

</details>

## 🔧 Technical Implementation Highlights

### ⚡ Smart Caching Strategy
```python
# Cache key: user_id + resume_content_hash + job_details_hash
def get_cached_analysis(user_id, resume_text, job_desc, job_title):
    resume_fingerprint = hashlib.md5(resume_text.encode()).hexdigest()
    job_fingerprint = hashlib.md5(f"{job_title}_{job_desc}".encode()).hexdigest()
    return f"analysis:{user_id}:{resume_fingerprint}:{job_fingerprint}"
```

## 🧵 Performance Optimization

- **Async/await background AI processing**  
- **Connection pooling** with SQLAlchemy  
- **Efficient file cleanup** to reduce memory footprint  
- **Concurrent API calls** and file processing  

---

## 🛡️ Security Implementation

- **Password hashing** using `bcrypt` with salt  
- **ID hashing** with SHA-256 + secret pepper  
- **Strict input validation** and schema enforcement  
- **Configured CORS** for cross-origin protection  

---

## 💼 Business & User Impact

### 💰 Cost Efficiency
- **50% fewer AI API calls** via smart caching  
- Reduced infrastructure needs through async workloads  
- Horizontal scalability for concurrent users  

### ⚡ User Experience
- Instant results for cached analyses (**2.1s vs 12.4s**)  
- Reliable service uptime with fallback mode  
- Detailed, actionable resume feedback  

---

## 🧠 Technical Skills Demonstrated

| Domain | Skills |
|--------|--------|
| **Backend Development** | FastAPI, SQLAlchemy, PostgreSQL, Redis |
| **AI Integration** | Google Gemini AI, Prompt Engineering |
| **Security** | JWT, bcrypt, SHA-256, POPI Act Compliance |
| **System Design** | Async architecture, caching, microservices |
| **DevOps & Monitoring** | CI/CD readiness, metrics, error tracking |

---

## 🔮 Future Enhancements

### 🌍 Planned Features
- Multi-language resume analysis  
- Resume insights dashboard  
- Third-party integration API  
- Progressive Web App (PWA) frontend  

### ☁️ Scalability Improvements
- Kubernetes deployment  
- CDN integration for global speed  
- Distributed Redis cluster  
- Automated load testing  

---

## 📞 Technical Contact

This project demonstrates **advanced backend engineering expertise** focused on:

> ⚙️ Performance Optimization  
> 🤖 AI Integration  
> 🧱 Scalable System Architecture  
> 🔐 Security & Compliance  

Built with **cutting-edge technologies** and **production-grade engineering practices**.

**Performance-Optimized • AI-Powered • Production-Ready 🚀**