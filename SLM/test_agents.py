"""
개별 에이전트 디버그 스크립트 - 허깅페이스 모델 테스트
"""
import asyncio
from llm_handler import LLMHandler
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

async def test_individual_agents():
    """각 에이전트를 개별적으로 테스트"""
    
    print("🔍 허깅페이스 모델 기반 에이전트 테스트 시작\n")
    
    # 1. DialoGPT-large 모델 테스트 (법률 전문가용)
    print("=== Microsoft DialoGPT-large 테스트 ===")
    try:
        large_handler = LLMHandler(model_name="microsoft/DialoGPT-large", temperature=0.2)
        response = large_handler.get_response("금융소비자보호법에 대해 설명해주세요.")
        print("✅ DialoGPT-large 성공:", response[:100] + "...")
    except Exception as e:
        print("❌ DialoGPT-large 실패:", str(e))
    
    print()
    
    # 2. DialoGPT-medium 모델 테스트 (기술 분석가용)
    print("=== Microsoft DialoGPT-medium 테스트 ===")
    try:
        medium_handler = LLMHandler(model_name="microsoft/DialoGPT-medium", temperature=0.3)
        response = medium_handler.get_response("대환대출이란 무엇인가요?")
        print("✅ DialoGPT-medium 성공:", response[:100] + "...")
    except Exception as e:
        print("❌ DialoGPT-medium 실패:", str(e))
    
    print()
    
    # 3. 다른 허깅페이스 모델 테스트
    print("=== 기타 허깅페이스 모델 테스트 ===")
    try:
        # 한국어에 특화된 모델 테스트
        korean_handler = LLMHandler(model_name="beomi/KoAlpaca-Polyglot-12.8B", temperature=0.4)
        response = korean_handler.get_response("안녕하세요, 테스트입니다.")
        print("✅ KoAlpaca-Polyglot 성공:", response[:100] + "...")
    except Exception as e:
        print("❌ KoAlpaca-Polyglot 실패:", str(e))
    
    print()
    
    # 4. 에이전트별 모델 설정 테스트
    print("=== 에이전트별 모델 설정 테스트 ===")
    try:
        from worker_agents import LegalExpertAgent, TechnicalAnalystAgent, GeneralKnowledgeAgent
        from memory_manager import MemoryManager
        from feedback_system import FeedbackSystem
        
        memory_manager = MemoryManager()
        feedback_system = FeedbackSystem()
        
        # 법률 전문가 에이전트 테스트
        legal_agent = LegalExpertAgent(memory_manager, feedback_system)
        print("✅ LegalExpertAgent 초기화 성공")
        
        # 기술 분석가 에이전트 테스트
        tech_agent = TechnicalAnalystAgent(memory_manager, feedback_system)
        print("✅ TechnicalAnalystAgent 초기화 성공")
        
        # 일반 지식 에이전트 테스트
        general_agent = GeneralKnowledgeAgent(memory_manager, feedback_system)
        print("✅ GeneralKnowledgeAgent 초기화 성공")
        
    except Exception as e:
        print("❌ 에이전트 초기화 실패:", str(e))

if __name__ == "__main__":
    asyncio.run(test_individual_agents()) 