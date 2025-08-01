"""
LangGraph 기반 멀티 에이전트 시스템 메인 실행 파일
"""
import asyncio
import json
import time
from typing import Dict, List, Any

from langgraph_multi_agent_system import LangGraphMultiAgentSystem


class LangGraphMain:
    """LangGraph 멀티 에이전트 시스템의 메인 인터페이스"""
    
    def __init__(self):
        print("🤖 LangGraph 멀티 에이전트 시스템 시작 중...")
        self.system = LangGraphMultiAgentSystem()
        print("✅ LangGraph 시스템 초기화 완료!")
        
    async def process_single_query(self, query: str) -> Dict[str, Any]:
        """단일 쿼리 처리"""
        print(f"\n🔍 쿼리 처리 시작: {query}")
        print("-" * 50)
        
        start_time = time.time()
        result = await self.system.process_user_query(query)
        execution_time = time.time() - start_time
        
        print("-" * 50)
        print(f"⏱️ 총 실행 시간: {execution_time:.2f}초")
        print(f"✅ 성공: {result.get('success', False)}")
        
        if result.get('success', False):
            print(f"📝 최종 답변: {result.get('final_answer', '')[:200]}...")
            print(f"🔧 사용된 소스: {len(result.get('consolidated_sources', []))}개")
            quality = result.get('response_quality', {})
            print(f"⭐ 품질 점수: {quality.get('overall_score', 0):.2f} ({quality.get('quality_level', 'unknown')})")
        else:
            print(f"❌ 오류: {result.get('error_message', '알 수 없는 오류')}")
        
        return result
    
    async def run_interactive_mode(self):
        """대화형 모드 실행"""
        print("\n🎯 LangGraph 멀티 에이전트 시스템 - 대화형 모드")
        print("💡 'quit', 'exit', 'q'를 입력하면 종료됩니다.")
        print("💡 'status'를 입력하면 시스템 상태를 확인할 수 있습니다.")
        print("💡 'reset'을 입력하면 시스템을 리셋할 수 있습니다.")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n사용자: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 시스템을 종료합니다.")
                    break
                
                if user_input.lower() == 'status':
                    await self._show_system_status()
                    continue
                    
                if user_input.lower() == 'reset':
                    self.system.reset_system()
                    print("🔄 시스템이 리셋되었습니다.")
                    continue
                
                if not user_input:
                    print("❓ 질문을 입력해주세요.")
                    continue
                
                # 쿼리 처리
                result = await self.process_single_query(user_input)
                
                # 결과 출력
                print(f"\n🤖 AI 답변:")
                print(f"{result.get('final_answer', '답변을 생성할 수 없습니다.')}")
                
                # 추천사항 출력
                recommendations = result.get('recommendations', [])
                if recommendations:
                    print(f"\n💡 추천사항:")
                    for i, rec in enumerate(recommendations, 1):
                        print(f"  {i}. {rec}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Ctrl+C로 종료되었습니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
                print("🔄 시스템을 계속 실행합니다...")
    
    async def _show_system_status(self):
        """시스템 상태 출력"""
        print("\n📊 LangGraph 시스템 상태:")
        print("-" * 40)
        
        status = self.system.get_system_status()
        
        # 기본 통계
        stats = status.get("system_stats", {})
        print(f"📈 총 쿼리 수: {stats.get('total_queries', 0)}")
        print(f"✅ 성공한 쿼리: {stats.get('successful_queries', 0)}")
        print(f"❌ 실패한 쿼리: {stats.get('failed_queries', 0)}")
        print(f"⏱️ 평균 응답 시간: {stats.get('average_response_time', 0):.2f}초")
        print(f"💚 시스템 건강도: {stats.get('system_health', 'unknown')}")
        
        # 워크플로우 정보
        workflow_info = status.get("workflow_info", {})
        print(f"\n🔧 워크플로우 정보:")
        print(f"  - 노드 수: {len(workflow_info.get('nodes', []))}")
        print(f"  - 노드 목록: {', '.join(workflow_info.get('nodes', []))}")
        print(f"  - 엣지 수: {workflow_info.get('edges', 0)}")
        print(f"  - 타입: {workflow_info.get('type', 'unknown')}")
        
        # 건강 상태
        health = status.get("system_health", {})
        print(f"\n💊 건강 상태:")
        print(f"  - 상태: {'정상' if health.get('healthy', False) else '비정상'}")
        if health.get("issues"):
            print(f"  - 문제점: {', '.join(health.get('issues', []))}")
    
    async def run_batch_test(self):
        """배치 테스트 실행"""
        test_queries = [
            "금융소비자보호법에 대해 설명해주세요",
            "대환대출이란 무엇인가요?",
            "은행에서 부당한 대출 거절을 당했을 때 어떻게 해야 하나요?",
            "금융감독원에 신고하는 방법을 알려주세요"
        ]
        
        print(f"\n🧪 배치 테스트 시작 ({len(test_queries)}개 쿼리)")
        print("=" * 60)
        
        start_time = time.time()
        results = await self.system.batch_process_queries(test_queries)
        total_time = time.time() - start_time
        
        print(f"\n📊 배치 테스트 결과:")
        print(f"⏱️ 총 실행 시간: {total_time:.2f}초")
        print(f"⚡ 평균 쿼리 시간: {total_time/len(test_queries):.2f}초")
        
        successful = sum(1 for r in results if r.get('success', False))
        print(f"✅ 성공률: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")
        
        for i, (query, result) in enumerate(zip(test_queries, results), 1):
            status = "✅" if result.get('success', False) else "❌"
            exec_time = result.get('execution_time', 0)
            print(f"  {status} 쿼리 {i}: {exec_time:.2f}초")
        
        return results
    
    async def compare_with_original(self, query: str):
        """기존 시스템과 성능 비교"""
        print(f"\n🔄 시스템 비교 테스트: {query}")
        print("=" * 60)
        
        # LangGraph 시스템 테스트
        print("🆕 LangGraph 시스템 실행 중...")
        langgraph_start = time.time()
        langgraph_result = await self.system.process_user_query(query)
        langgraph_time = time.time() - langgraph_start
        
        # 기존 시스템 테스트 (import 후 실행)
        try:
            from multi_agent_system import MultiAgentSystem
            print("🔧 기존 시스템 실행 중...")
            original_system = MultiAgentSystem()
            original_start = time.time()
            original_result = await original_system.process_user_query(query)
            original_time = time.time() - original_start
            
            # 비교 결과 출력
            print(f"\n📊 성능 비교 결과:")
            print(f"🆕 LangGraph: {langgraph_time:.2f}초, 성공: {langgraph_result.get('success', False)}")
            print(f"🔧 기존 시스템: {original_time:.2f}초, 성공: {original_result.get('success', False)}")
            
            if langgraph_time < original_time:
                improvement = ((original_time - langgraph_time) / original_time) * 100
                print(f"⚡ LangGraph가 {improvement:.1f}% 더 빠름")
            else:
                difference = ((langgraph_time - original_time) / original_time) * 100
                print(f"⏱️ LangGraph가 {difference:.1f}% 더 느림")
                
            return {
                "langgraph": langgraph_result,
                "original": original_result,
                "performance": {
                    "langgraph_time": langgraph_time,
                    "original_time": original_time
                }
            }
            
        except ImportError:
            print("⚠️ 기존 시스템을 import할 수 없습니다.")
            return {"langgraph": langgraph_result}


async def main():
    """메인 실행 함수"""
    print("🚀 LangGraph 멀티 에이전트 시스템")
    print("=" * 50)
    
    try:
        app = LangGraphMain()
        
        print("\n사용 가능한 모드:")
        print("1. 대화형 모드 (interactive)")
        print("2. 배치 테스트 (batch)")
        print("3. 시스템 비교 (compare)")
        print("4. 단일 테스트 (single)")
        
        mode = input("\n실행할 모드를 선택하세요 (1-4): ").strip()
        
        if mode == "1" or mode.lower() == "interactive":
            await app.run_interactive_mode()
        elif mode == "2" or mode.lower() == "batch":
            await app.run_batch_test()
        elif mode == "3" or mode.lower() == "compare":
            query = input("비교할 쿼리를 입력하세요: ").strip()
            if query:
                await app.compare_with_original(query)
        elif mode == "4" or mode.lower() == "single":
            query = input("테스트할 쿼리를 입력하세요: ").strip()
            if query:
                await app.process_single_query(query)
        else:
            print("❌ 잘못된 선택입니다. 대화형 모드로 실행합니다.")
            await app.run_interactive_mode()
            
    except Exception as e:
        print(f"❌ 시스템 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 