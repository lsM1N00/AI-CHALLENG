"""
개별 에이전트 디버그 스크립트
"""
import asyncio
from llm_handler import LLMHandler
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

async def test_individual_agents():
    """각 에이전트를 개별적으로 테스트"""
    
    print("🔍 개별 에이전트 테스트 시작\n")
    
    # 1. OpenAI GPT-4.1 테스트
    print("=== OpenAI GPT-4.1 테스트 ===")
    try:
        openai_handler = LLMHandler(provider="openai", model_name="gpt-4.1", temperature=0.3)
        response = openai_handler.get_response("안녕하세요, 테스트입니다.")
        print("✅ OpenAI 성공:", response[:50] + "...")
    except Exception as e:
        print("❌ OpenAI 실패:", str(e))
    
    print()
    
    # 2. Anthropic Claude 테스트
    print("=== Anthropic Claude Sonnet 4 테스트 ===")
    try:
        claude_handler = LLMHandler(provider="anthropic", model_name="claude-sonnet-4-20250514", temperature=0.3)
        response = claude_handler.get_response("안녕하세요, 테스트입니다.")
        print("✅ Anthropic 성공:", response[:50] + "...")
    except Exception as e:
        print("❌ Anthropic 실패:", str(e))
    
    print()
    
    # 3. Google Gemini 테스트
    print("=== Google Gemini 2.5 Pro 테스트 ===")
    try:
        gemini_handler = LLMHandler(provider="google", model_name="gemini-2.5-pro", temperature=0.3)
        response = gemini_handler.get_response("안녕하세요, 테스트입니다.")
        print("✅ Google 성공:", response[:50] + "...")
    except Exception as e:
        print("❌ Google 실패:", str(e))

if __name__ == "__main__":
    asyncio.run(test_individual_agents()) 