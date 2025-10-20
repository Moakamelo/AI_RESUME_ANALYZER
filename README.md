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

The **AI Resume Analyzer** is a **full-stack, AI-powered system** that provides instant, detailed feedback on resume **ATS (Applicant Tracking System)** compatibility.  
It leverages **Google’s Gemini AI** for intelligent scoring and improvement suggestions — designed for **speed, scalability, and compliance**.

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

```mermaid
graph TD
    A[Client / UI] -->|API Request| B(FastAPI Backend)
    B -->|Auth| C[JWT Authentication]
    B -->|Cache Check| D[Redis Cache]
    B -->|DB Query| E[(PostgreSQL Database)]
    B -->|File Upload| F[Supabase Storage]
    B -->|AI Request| G[Google Gemini AI]
    D -->|Hit| B
    G -->|JSON Response| B
    E -->|Data| B
    F -->|Files| B
    B -->|JSON Response| A
