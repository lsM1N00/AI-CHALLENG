"""
멀티 에이전트 시스템 설정 파일 (API 키 없이도 사용 가능)
"""
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# === 데이터베이스 설정 ===
DB_NAME = os.getenv("DB_NAME", "financedb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "0717")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# === 허깅페이스 모델 설정 ===
# 액세스 토큰이 없어도 공개 모델을 사용할 수 있습니다
HUGGINGFACE_ACCESS_TOKEN = os.getenv("HUGGINGFACE_ACCESS_TOKEN", "")
HUGGINGFACE_BASE_URL = os.getenv("HUGGINGFACE_BASE_URL", "https://api-inference.huggingface.co")

# 액세스 토큰 설정 여부 확인
HAS_HUGGINGFACE_TOKEN = bool(HUGGINGFACE_ACCESS_TOKEN and HUGGINGFACE_ACCESS_TOKEN != "")

if not HAS_HUGGINGFACE_TOKEN:
    print("💡 HUGGINGFACE_ACCESS_TOKEN이 설정되지 않았습니다.")
    print("💡 공개 모델을 사용하여 시스템이 작동합니다.")
    print("💡 더 나은 성능을 원한다면 .env 파일에 액세스 토큰을 설정하세요.")
else:
    print("✅ HUGGINGFACE_ACCESS_TOKEN이 설정되었습니다.")

# === Google Custom Search 설정 ===
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "your_google_api_key_here")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "your_google_cse_id_here")

# Google Custom Search Engine IDs
CASE_LAW_SEARCH_ENGINE_ID = os.getenv("CASE_LAW_SEARCH_ENGINE_ID", "your_case_law_search_engine_id")
FAQ_SEARCH_ENGINE_ID = os.getenv("FAQ_SEARCH_ENGINE_ID", "your_faq_search_engine_id")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID", "your_general_search_engine_id")

# === 임베딩 모델 설정 ===
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

# === 시스템 설정 ===
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
MAX_MEMORY_ITEMS = int(os.getenv("MAX_MEMORY_ITEMS", "1000"))
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))

# === 로깅 설정 ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "agent_system.log")

# === 성능 설정 ===
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))

# === 모델 사용 모드 설정 ===
# True: API 키가 있을 때만 사용, False: API 키가 없어도 공개 모델 사용
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"

if REQUIRE_API_KEY and not HAS_HUGGINGFACE_TOKEN:
    print("⚠️ REQUIRE_API_KEY가 true로 설정되어 있지만 API 키가 없습니다.")
    print("⚠️ 시스템이 작동하지 않을 수 있습니다.")
    print("💡 .env 파일에 HUGGINGFACE_ACCESS_TOKEN를 설정하거나 REQUIRE_API_KEY를 false로 설정하세요.")
