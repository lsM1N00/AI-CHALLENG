"""
워커 에이전트 초기화 디버그 스크립트
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from worker_agents import WorkerAgentPool
from memory_manager import MemoryManager
from feedback_system import FeedbackSystem

async def test_worker_agents():
    """워커 에이전트들을 실제로 초기화하고 테스트"""
    
    print("🔍 워커 에이전트 초기화 테스트 시작\n")
    
    try:
        # 메모리 매니저와 피드백 시스템 초기화
        print("1. 메모리 매니저 초기화...")
        memory_manager = MemoryManager()
        print("✅ 메모리 매니저 성공")
        
        print("2. 피드백 시스템 초기화...")
        feedback_system = FeedbackSystem()
        print("✅ 피드백 시스템 성공")
        
        print("3. 워커 에이전트 풀 초기화...")
        agent_pool = WorkerAgentPool()
        print("✅ 워커 에이전트 풀 성공")
        
        # 각 에이전트별로 개별 테스트
        print("\n=== 개별 에이전트 테스트 ===")
        
        test_query = "안녕하세요, 테스트입니다."
        
        for agent_id, agent in agent_pool.agents.items():
            print(f"\n--- {agent_id} 에이전트 테스트 ---")
            try:
                print(f"  모델 설정: {agent.model_config}")
                print(f"  전문 분야: {agent.specializations}")
                
                # 개별 에이전트 테스트
                response = await agent.process_query(test_query)
                
                if response.success:
                    print(f"  ✅ {agent_id} 성공: {response.response[:50]}...")
                    print(f"  실행 시간: {response.execution_time:.2f}초")
                    print(f"  소스 개수: {len(response.sources)}")
                else:
                    print(f"  ❌ {agent_id} 실패: {response.error}")
                    
            except Exception as e:
                print(f"  ❌ {agent_id} 초기화 오류: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # 전체 에이전트 동시 실행 테스트
        print(f"\n=== 전체 에이전트 동시 실행 테스트 ===")
        try:
            responses = await agent_pool.process_query_all_agents(test_query)
            
            successful = [r for r in responses if r.success]
            failed = [r for r in responses if not r.success]
            
            print(f"성공한 에이전트: {len(successful)}/{len(responses)}")
            print(f"실패한 에이전트: {len(failed)}/{len(responses)}")
            
            for response in failed:
                print(f"  ❌ {response.agent_id} 실패: {response.error}")
                
        except Exception as e:
            print(f"❌ 동시 실행 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ 초기화 오류: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_worker_agents()) 