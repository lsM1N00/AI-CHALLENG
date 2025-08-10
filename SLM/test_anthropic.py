from google import genai
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 클라이언트 초기화 (HttpOptions 없이)
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# 텍스트 요청 보내기
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="안녕하세요."
)

# 응답 출력
print(response.text)