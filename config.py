"""
멀티 에이전트 시스템 설정 파일
"""
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# === 데이터베이스 설정 ===
DB_NAME = os.getenv("DB_NAME", "financedb")
DB_USER = os.getenv("DB_USER", "sangmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "0717")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# === LLM 모델 설정 ===
# 기본 LLM (Groq)
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3-70b-8192")
LLM_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")

# Ollama 설정 (로컬 실행용)
LLM_MODEL = "llama3"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# === 임베딩 모델 설정 ===
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

# === Google Custom Search 설정 ===
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "your_google_api_key_here")

# 검색 엔진 ID들
CASE_LAW_SEARCH_ENGINE_ID = os.getenv("CASE_LAW_SEARCH_ENGINE_ID", "your_case_law_engine_id")  # 판례 검색 엔진
FAQ_SEARCH_ENGINE_ID = os.getenv("FAQ_SEARCH_ENGINE_ID", "your_faq_engine_id")  # FAQ 검색 엔진
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID", "your_general_engine_id")  # 일반/기본 검색 엔진
