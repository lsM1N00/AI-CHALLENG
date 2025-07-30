#!/usr/bin/env python3
"""
멀티 에이전트 시스템 상태 직접 테스트
"""
import asyncio
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

from multi_agent_system import MultiAgentSystem

async def test_system_health():
    """시스템 상태 직접 테스트"""
    print("🔍 멀티 에이전트 시스템 상태 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 시스템 초기화
        print("1. 시스템 초기화 중...")
        system = MultiAgentSystem()
        print("✅ 시스템 초기화 성공")
        
        # 2. 시스템 전체 상태 확인
        print("\n2. 시스템 전체 상태 확인 중...")
        system_status = system.get_system_status()
        print(f"✅ 시스템 상태: {system_status}")
        
        # 3. 간단한 쿼리 테스트
        print("\n3. 간단한 쿼리 테스트 중...")
        test_query = "안녕하세요"
        
        print(f"테스트 쿼리: {test_query}")
        result = await system.process_user_query(test_query)
        
        print(f"\n📊 테스트 결과:")
        print(f"   응답: {result.get('response', 'N/A')[:100]}...")
        print(f"   품질 등급: {result.get('quality_grade', 'N/A')}")
        print(f"   처리 시간: {result.get('execution_time', 'N/A')}초")
        print(f"   참여 에이전트: {result.get('source_agents', [])}")
        
        if result.get('quality_grade') == 'ERROR':
            print("❌ 시스템 에러 발생")
            return False
        else:
            print("✅ 시스템 정상 작동")
            return True
            
    except Exception as e:
        print(f"❌ 시스템 테스트 실패: {e}")
        print(f"오류 타입: {type(e).__name__}")
        import traceback
        print("전체 트레이스백:")
        traceback.print_exc()
        return False

async def main():
    """메인 함수"""
    success = await test_system_health()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 멀티 에이전트 시스템이 정상적으로 작동합니다!")
    else:
        print("💥 멀티 에이전트 시스템에 문제가 있습니다.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 