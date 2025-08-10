"""
LangGraph 체크포인터 기능 테스트
"""
import asyncio
import time
from langgraph_multi_agent_system import LangGraphMultiAgentSystem


async def test_checkpointer_functionality():
    """체크포인터 기능 테스트"""
    print("🧪 LangGraph 체크포인터 기능 테스트 시작")
    print("=" * 60)
    
    # 시스템 초기화
    system = LangGraphMultiAgentSystem()
    
    # 테스트 사용자들
    test_users = ["user1", "user2", "user3"]
    
    try:
        # 1. 여러 사용자로 쿼리 처리 테스트
        print("\n1️⃣ 여러 사용자로 쿼리 처리 테스트")
        print("-" * 40)
        
        for user_id in test_users:
            print(f"\n👤 사용자 {user_id}로 쿼리 처리 중...")
            
            # 간단한 쿼리로 테스트
            query = f"{user_id}의 테스트 질문입니다."
            result = await system.process_user_query(query, user_id)
            
            if result.get('success', False):
                print(f"✅ {user_id} 쿼리 처리 성공")
                print(f"   답변: {result.get('final_answer', '')[:50]}...")
            else:
                print(f"❌ {user_id} 쿼리 처리 실패: {result.get('error_message', '')}")
        
        # 2. 대화 히스토리 조회 테스트
        print("\n2️⃣ 대화 히스토리 조회 테스트")
        print("-" * 40)
        
        for user_id in test_users:
            print(f"\n📚 사용자 {user_id}의 대화 히스토리:")
            history = system.get_conversation_history(user_id)
            
            if history:
                print(f"   📝 대화 수: {len(history)}개")
                for i, conv in enumerate(history, 1):
                    print(f"   {i}. 질문: {conv.get('user_query', 'N/A')[:30]}...")
                    print(f"      답변: {conv.get('ai_response', 'N/A')[:30]}...")
            else:
                print(f"   📝 대화 히스토리가 없습니다.")
        
        # 3. 모든 스레드 정보 조회 테스트
        print("\n3️⃣ 모든 대화 스레드 정보 조회 테스트")
        print("-" * 40)
        
        threads = system.get_all_conversation_threads()
        print(f"총 {len(threads)}개의 스레드가 있습니다:")
        
        for thread in threads:
            print(f"   👤 사용자: {thread.get('user_id')}")
            print(f"   🧵 스레드 ID: {thread.get('thread_id')}")
            print(f"   📊 데이터 존재: {'✅' if thread.get('has_data') else '❌'}")
            print(f"   ⏰ 생성 시간: {thread.get('created_at')}")
            print()
        
        # 4. 데이터 내보내기 테스트
        print("\n4️⃣ 데이터 내보내기 테스트")
        print("-" * 40)
        
        for user_id in test_users:
            print(f"\n📤 사용자 {user_id}의 데이터 내보내기:")
            
            # JSON 형식으로 내보내기
            json_export = system.export_conversation_data(user_id, "json")
            if not json_export.startswith("데이터 내보내기 실패"):
                print(f"   ✅ JSON 내보내기 성공 (길이: {len(json_export)} 문자)")
            else:
                print(f"   ❌ JSON 내보내기 실패: {json_export}")
            
            # TXT 형식으로 내보내기
            txt_export = system.export_conversation_data(user_id, "txt")
            if not txt_export.startswith("데이터 내보내기 실패"):
                print(f"   ✅ TXT 내보내기 성공 (길이: {len(txt_export)} 문자)")
            else:
                print(f"   ❌ TXT 내보내기 실패: {txt_export}")
        
        # 5. 특정 사용자의 대화 히스토리 삭제 테스트
        print("\n5️⃣ 대화 히스토리 삭제 테스트")
        print("-" * 40)
        
        test_user = test_users[0]
        print(f"🗑️ 사용자 {test_user}의 대화 히스토리 삭제 중...")
        
        # 삭제 전 히스토리 확인
        before_delete = system.get_conversation_history(test_user)
        print(f"   삭제 전 대화 수: {len(before_delete)}개")
        
        # 히스토리 삭제
        system.clear_conversation_history(test_user)
        
        # 삭제 후 히스토리 확인
        after_delete = system.get_conversation_history(test_user)
        print(f"   삭제 후 대화 수: {len(after_delete)}개")
        
        if len(after_delete) == 0:
            print(f"   ✅ {test_user}의 대화 히스토리 삭제 성공")
        else:
            print(f"   ❌ {test_user}의 대화 히스토리 삭제 실패")
        
        # 6. 시스템 상태 확인 테스트
        print("\n6️⃣ 시스템 상태 확인 테스트")
        print("-" * 40)
        
        status = system.get_system_status()
        print(f"📊 총 쿼리 수: {status.get('total_queries', 0)}")
        print(f"✅ 성공한 쿼리: {status.get('successful_queries', 0)}")
        print(f"❌ 실패한 쿼리: {status.get('failed_queries', 0)}")
        print(f"💬 활성 대화 수: {status.get('active_conversations', 0)}")
        
        print("\n🎉 체크포인터 기능 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 시스템 정리
        print("\n🧹 시스템 정리 중...")
        for user_id in test_users:
            try:
                system.clear_conversation_history(user_id)
            except:
                pass
        print("✅ 정리 완료")


async def test_conversation_persistence():
    """대화 내용 지속성 테스트"""
    print("\n🧪 대화 내용 지속성 테스트")
    print("=" * 60)
    
    system = LangGraphMultiAgentSystem()
    test_user = "persistence_test_user"
    
    try:
        # 1. 첫 번째 대화
        print(f"\n1️⃣ 첫 번째 대화 시작 (사용자: {test_user})")
        query1 = "안녕하세요, 첫 번째 질문입니다."
        result1 = await system.process_user_query(query1, test_user)
        
        if result1.get('success', False):
            print(f"   ✅ 첫 번째 대화 성공")
            print(f"   📝 답변: {result1.get('final_answer', '')[:50]}...")
        else:
            print(f"   ❌ 첫 번째 대화 실패: {result1.get('error_message', '')}")
        
        # 2. 두 번째 대화 (연속성 테스트)
        print(f"\n2️⃣ 두 번째 대화 시작 (사용자: {test_user})")
        query2 = "이전 대화를 기억하고 있나요?"
        result2 = await system.process_user_query(query2, test_user)
        
        if result2.get('success', False):
            print(f"   ✅ 두 번째 대화 성공")
            print(f"   📝 답변: {result2.get('final_answer', '')[:50]}...")
        else:
            print(f"   ❌ 두 번째 대화 실패: {result2.get('error_message', '')}")
        
        # 3. 대화 히스토리 확인
        print(f"\n3️⃣ 대화 히스토리 확인")
        history = system.get_conversation_history(test_user)
        print(f"   📚 총 대화 수: {len(history)}개")
        
        for i, conv in enumerate(history, 1):
            print(f"   {i}. 질문: {conv.get('user_query', 'N/A')}")
            print(f"      답변: {conv.get('ai_response', 'N/A')[:50]}...")
        
        # 4. 정리
        system.clear_conversation_history(test_user)
        print(f"\n✅ 지속성 테스트 완료 및 정리")
        
    except Exception as e:
        print(f"\n❌ 지속성 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """메인 테스트 함수"""
    print("🚀 LangGraph 체크포인터 기능 종합 테스트")
    print("=" * 60)
    
    # 기본 체크포인터 기능 테스트
    await test_checkpointer_functionality()
    
    # 대화 내용 지속성 테스트
    await test_conversation_persistence()
    
    print("\n🎯 모든 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main()) 