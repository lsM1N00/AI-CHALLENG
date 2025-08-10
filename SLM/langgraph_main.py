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
        self.current_user = "default"  # 현재 사용자 ID
        print("✅ LangGraph 시스템 초기화 완료!")
        
    async def process_single_query(self, query: str, user_id: str = None) -> Dict[str, Any]:
        """단일 쿼리 처리"""
        if user_id is None:
            user_id = self.current_user
            
        print(f"\n🔍 쿼리 처리 시작: {query}")
        print(f"👤 사용자 ID: {user_id}")
        print("-" * 50)
        
        start_time = time.time()
        result = await self.system.process_user_query(query, user_id)
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
        print("💡 'user <사용자ID>'를 입력하면 사용자를 변경할 수 있습니다.")
        print("💡 'history'를 입력하면 현재 사용자의 대화 히스토리를 확인할 수 있습니다.")
        print("💡 'clear_history'를 입력하면 현재 사용자의 대화 히스토리를 삭제할 수 있습니다.")
        print("💡 'export <형식>'을 입력하면 현재 사용자의 대화 데이터를 내보낼 수 있습니다. (예: export json, export txt)")
        print("💡 'threads'를 입력하면 모든 대화 스레드 정보를 확인할 수 있습니다.")
        print("=" * 60)
        
        while True:
            try:
                user_input = input(f"\n사용자({self.current_user}): ").strip()
                
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
                
                if user_input.lower().startswith('user '):
                    new_user = user_input[5:].strip()
                    if new_user:
                        self.current_user = new_user
                        print(f"👤 사용자가 '{new_user}'로 변경되었습니다.")
                    else:
                        print("❓ 사용자 ID를 입력해주세요. (예: user john)")
                    continue
                
                if user_input.lower() == 'history':
                    await self._show_conversation_history()
                    continue
                
                if user_input.lower() == 'clear_history':
                    self.system.clear_conversation_history(self.current_user)
                    print(f"🗑️ 사용자 '{self.current_user}'의 대화 히스토리가 삭제되었습니다.")
                    continue
                
                if user_input.lower().startswith('export '):
                    format_type = user_input[7:].strip()
                    if format_type in ['json', 'txt']:
                        await self._export_conversation_data(format_type)
                    else:
                        print("❓ 지원하는 형식: json, txt (예: export json)")
                    continue
                
                if user_input.lower() == 'threads':
                    await self._show_all_threads()
                    continue
                
                if not user_input:
                    print("❓ 질문을 입력해주세요.")
                    continue
                
                # 쿼리 처리
                result = await self.process_single_query(user_input, self.current_user)
                
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
    
    async def _show_conversation_history(self):
        """현재 사용자의 대화 히스토리 출력"""
        print(f"\n📚 사용자 '{self.current_user}'의 대화 히스토리:")
        print("-" * 50)
        
        history = self.system.get_conversation_history(self.current_user)
        
        if not history:
            print("📝 대화 히스토리가 없습니다.")
            return
        
        for i, conversation in enumerate(history, 1):
            print(f"\n{i}. 시간: {conversation.get('timestamp', 'N/A')}")
            print(f"   질문: {conversation.get('user_query', 'N/A')[:100]}...")
            print(f"   답변: {conversation.get('ai_response', 'N/A')[:100]}...")
            print(f"   품질: {conversation.get('quality_score', 'N/A')}")
            print(f"   소스: {len(conversation.get('sources', []))}개")
    
    async def _show_system_status(self):
        """시스템 상태 출력"""
        print("\n📊 LangGraph 시스템 상태:")
        print("-" * 40)
        
        status = self.system.get_system_status()
        
        # 기본 통계
        print(f"📈 총 쿼리 수: {status.get('total_queries', 0)}")
        print(f"✅ 성공한 쿼리: {status.get('successful_queries', 0)}")
        print(f"❌ 실패한 쿼리: {status.get('failed_queries', 0)}")
        print(f"⏱️ 평균 응답 시간: {status.get('average_response_time', 0):.2f}초")
        print(f"🏥 시스템 상태: {status.get('system_health', 'unknown')}")
        
        # 체크포인터 관련 정보
        print(f"💬 활성 대화 수: {status.get('active_conversations', 0)}")
        print(f"👤 현재 사용자: {self.current_user}")
        
        # 메모리 사용량
        memory_info = status.get('memory_usage', {})
        if memory_info:
            print(f"💾 메모리 사용량: {memory_info.get('total_memory', 'N/A')}")
            print(f"📁 저장된 상호작용: {memory_info.get('stored_interactions', 0)}개")
    
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

    async def _export_conversation_data(self, format_type: str):
        """대화 데이터 내보내기"""
        print(f"\n📤 사용자 '{self.current_user}'의 대화 데이터를 {format_type.upper()} 형식으로 내보내는 중...")
        
        export_result = self.system.export_conversation_data(self.current_user, format_type)
        
        if export_result.startswith("데이터 내보내기 실패") or export_result.startswith("사용자를 찾을 수 없습니다") or export_result.startswith("내보낼 대화 내용이 없습니다"):
            print(f"❌ {export_result}")
        else:
            print(f"✅ 데이터 내보내기 완료!")
            
            if format_type == 'json':
                # JSON 데이터를 파일로 저장
                filename = f"conversation_{self.current_user}_{int(time.time())}.json"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(export_result)
                    print(f"💾 파일로 저장됨: {filename}")
                except Exception as e:
                    print(f"❌ 파일 저장 실패: {e}")
                    print(f"📄 데이터 내용:\n{export_result}")
            else:
                # TXT 데이터를 파일로 저장
                filename = f"conversation_{self.current_user}_{int(time.time())}.txt"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(export_result)
                    print(f"💾 파일로 저장됨: {filename}")
                except Exception as e:
                    print(f"❌ 파일 저장 실패: {e}")
                    print(f"📄 데이터 내용:\n{export_result}")
    
    async def _show_all_threads(self):
        """모든 대화 스레드 정보 출력"""
        print(f"\n🧵 모든 대화 스레드 정보:")
        print("-" * 50)
        
        threads = self.system.get_all_conversation_threads()
        
        if not threads:
            print("📝 활성 대화 스레드가 없습니다.")
            return
        
        for i, thread in enumerate(threads, 1):
            print(f"\n{i}. 사용자 ID: {thread.get('user_id', 'N/A')}")
            print(f"   스레드 ID: {thread.get('thread_id', 'N/A')}")
            print(f"   데이터 존재: {'✅' if thread.get('has_data', False) else '❌'}")
            print(f"   생성 시간: {thread.get('created_at', 'N/A')}")
            
            if thread.get('user_id') == self.current_user:
                print(f"   👤 현재 사용자")
        
        print(f"\n총 {len(threads)}개의 스레드가 있습니다.")


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