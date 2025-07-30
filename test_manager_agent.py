#!/usr/bin/env python3
"""
Manager Agent 단독 테스트
"""
import asyncio
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def test_manager_agent_init():
    """Manager Agent 초기화 테스트"""
    print("🔍 Manager Agent 초기화 테스트")
    print("=" * 50)
    
    try:
        print("1. Manager Agent 임포트...")
        from manager_agent import ManagerAgent
        print("✅ 임포트 성공")
        
        print("\n2. Manager Agent 초기화...")
        manager = ManagerAgent()
        print("✅ 초기화 성공")
        
        print("\n3. 시스템 상태 확인...")
        status = manager.get_system_status()
        print(f"✅ 시스템 상태: {len(str(status))} 문자")
        
        print("\n4. LLM Handler 테스트...")
        # 간단한 LLM 테스트
        response = manager.llm_handler.get_response("안녕하세요")
        print(f"✅ LLM 응답: {len(response)} 문자")
        
        return True
        
    except Exception as e:
        print(f"❌ Manager Agent 테스트 실패: {e}")
        print(f"오류 타입: {type(e).__name__}")
        import traceback
        print("전체 트레이스백:")
        traceback.print_exc()
        return False

async def test_manager_agent_query():
    """Manager Agent 쿼리 처리 테스트"""
    print("\n" + "=" * 50)
    print("🔍 Manager Agent 쿼리 처리 테스트")
    print("=" * 50)
    
    try:
        from manager_agent import ManagerAgent
        
        manager = ManagerAgent()
        print("Manager Agent 초기화 완료")
        
        # 간단한 쿼리 테스트
        test_query = "안녕하세요"
        print(f"테스트 쿼리: {test_query}")
        
        result = await manager.process_query(test_query)
        
        print(f"\n📊 결과:")
        print(f"   응답: {result.final_answer[:100]}...")
        print(f"   소스 에이전트: {result.source_agents}")
        print(f"   실행 시간: {result.execution_time:.2f}초")
        print(f"   품질 메트릭: {result.quality_metrics}")
        
        return True
        
    except Exception as e:
        print(f"❌ Manager Agent 쿼리 테스트 실패: {e}")
        print(f"오류 타입: {type(e).__name__}")
        import traceback
        print("전체 트레이스백:")
        traceback.print_exc()
        return False

async def main():
    """메인 함수"""
    # 1. 초기화 테스트
    init_success = test_manager_agent_init()
    
    if init_success:
        # 2. 쿼리 처리 테스트
        query_success = await test_manager_agent_query()
        
        print("\n" + "=" * 50)
        if query_success:
            print("🎉 Manager Agent가 정상적으로 작동합니다!")
        else:
            print("💥 Manager Agent 쿼리 처리에 문제가 있습니다.")
    else:
        print("\n💥 Manager Agent 초기화에 문제가 있습니다.")
        
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 