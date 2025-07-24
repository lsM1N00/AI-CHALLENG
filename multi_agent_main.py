"""
멀티 에이전트 시스템 메인 애플리케이션
"""
import asyncio
import time
from typing import Dict, Any

from multi_agent_system import MultiAgentSystem

class MultiAgentApp:
    """멀티 에이전트 시스템 애플리케이션"""
    
    def __init__(self):
        print("멀티 에이전트 시스템 초기화 중...")
        self.system = MultiAgentSystem()
        print("시스템 초기화 완료!")
        
    def display_welcome_message(self):
        """환영 메시지 표시"""
        print("\n" + "="*80)
        print("AI 멀티 에이전트 시스템")
        print("="*80)
        print("📋 시스템 구성:")
        print("   • 관리자 에이전트 (Manager Agent): 1개")
        print("   • 작업 에이전트 (Worker Agents): 3개")
        print("     - 법률 전문 에이전트 (LegalExpert)")
        print("     - 기술 분석 에이전트 (TechnicalAnalyst)")
        print("     - 일반 지식 에이전트 (GeneralKnowledge)")
        print("\n🔧 주요 기능:")
        print("   • 웹 검색 + RAG 검색")
        print("   • 메모리 관리 (단기/장기)")
        print("   • 피드백 및 자기 수정")
        print("   • 응답 품질 평가")
        print("   • 일관성 검증")
        print("\n📝 명령어:")
        print("   • 'exit' 또는 'quit': 종료")
        print("   • 'status': 시스템 상태 확인")
        print("   • 'reset': 시스템 리셋")
        print("   • 'help': 도움말 표시")
        print("="*80)
    
    def display_help(self):
        """도움말 표시"""
        print("\n📖 사용법 가이드:")
        print("1. 질문 예시:")
        print("   • '금융소비자보호법 제20조란 무엇인가요?'")
        print("   • '멀티 에이전트 시스템을 어떻게 구현하나요?'")
        print("   • '최신 AI 기술 동향은 어떤가요?'")
        print("\n2. 시스템 특징:")
        print("   • 3개의 전문 에이전트가 동시에 응답을 생성합니다")
        print("   • 관리자 에이전트가 최적의 답변을 선별하고 통합합니다")
        print("   • 각 응답에 신뢰도와 품질 점수가 제공됩니다")
        print("   • 추천 사항을 통해 더 나은 질문 방법을 제안합니다")
        print("\n3. 품질 지표:")
        print("   • 신뢰도 점수: 응답의 정확성 추정")
        print("   • 일관성 점수: 에이전트 간 합의 수준")
        print("   • 소스 활용도: 참조한 문서/웹 소스 품질")
        print("   • 실행 시간: 응답 생성에 소요된 시간")
    
    async def display_system_status(self):
        """시스템 상태 표시"""
        print("\n시스템 상태:")
        status = self.system.get_system_status()
        
        # 기본 통계
        stats = status["system_stats"]
        print(f"   총 쿼리 수: {stats['total_queries']}")
        print(f"   성공한 쿼리: {stats['successful_queries']}")
        print(f"   실패한 쿼리: {stats['failed_queries']}")
        print(f"   평균 응답 시간: {stats['average_response_time']:.2f}초")
        print(f"   시스템 건강도: {stats['system_health']}")
        
        # 시스템 건강 상태
        health = status["system_health"]
        health_status = "양호" if health["healthy"] else "문제"
        print(f"   상태: {health_status}")
        
        if health["issues"]:
            print(" 문제점:")
            for issue in health["issues"]:
                print(f"      • {issue}")
        
        # 성능 메트릭
        if "performance_metrics" in health:
            metrics = health["performance_metrics"]
            success_rate = metrics.get("success_rate", 0) * 100
            print(f"   성공률: {success_rate:.1f}%")
    
    def format_response(self, response: Dict[str, Any]) -> str:
        """응답을 사용자 친화적으로 포맷팅"""
        output = []
        
        # 헤더
        output.append("\n" + "="*80)
        output.append("AI 멀티 에이전트 응답")
        output.append("="*80)
        
        # 주요 답변
        output.append(f"\n답변:")
        output.append(f"{response['final_answer']}")
        
        # 품질 정보
        quality = response.get("response_quality", {})
        
        output.append(f"\n품질 정보:")
        output.append(f"   품질 등급: {quality.get('quality_level', 'unknown').upper()}")
        output.append(f"   전체 점수: {quality.get('overall_score', 0):.2f}")
        
        # 에이전트 정보
        source_agents = response.get("source_agents", [])
        output.append(f"\n참여 에이전트: {', '.join(source_agents)}")
        
        # 실행 정보
        execution_time = response.get("execution_time", 0)
        output.append(f"   처리 시간: {execution_time:.2f}초")
        
        # 품질 메트릭 세부사항
        quality_metrics = response.get("quality_metrics", {})
        if "individual_scores" in quality_metrics:
            output.append(f"\n 에이전트별 점수:")
            for agent, score in quality_metrics["individual_scores"].items():
                output.append(f"   • {agent}: {score:.2f}")
        
        # 소스 정보
        sources = response.get("sources", [])
        if sources:
            output.append(f"\n참조 소스 ({len(sources)}개):")
            for i, source in enumerate(sources[:3], 1):  # 상위 3개만 표시
                source_type = source.get("type", "unknown")
                if source_type == "document":
                    output.append(f"   {i}. [문서] {source.get('content', '')[:100]}...")
                elif source_type == "web":
                    output.append(f"   {i}. [웹] {source.get('title', '')}")
        
        # 추천 사항
        recommendations = response.get("recommendations", [])
        if recommendations:
            output.append(f"\n 추천 사항:")
            for rec in recommendations:
                output.append(f"   • {rec}")
        
        output.append("="*80)
        
        return "\n".join(output)
    

    
    async def run_interactive_mode(self):
        """대화형 모드 실행"""
        self.display_welcome_message()
        
        while True:
            try:
                print("\n" + "-"*50)
                user_input = input(" 질문을 입력하세요: ").strip()
                
                if not user_input:
                    continue
                
                # 명령어 처리
                if user_input.lower() in ['exit', 'quit', '종료']:
                    print("\n멀티 에이전트 시스템을 종료합니다. 감사합니다!")
                    break
                elif user_input.lower() == 'help':
                    self.display_help()
                    continue
                elif user_input.lower() == 'status':
                    await self.display_system_status()
                    continue
                elif user_input.lower() == 'reset':
                    self.system.reset_system()
                    print("시스템이 리셋되었습니다.")
                    continue
                
                # 쿼리 처리
                print(f"\n⏳ 멀티 에이전트 시스템이 질문을 처리하고 있습니다...")
                print("   (3개의 전문 에이전트가 동시에 작업 중)")
                
                start_time = time.time()
                response = await self.system.process_user_query(user_input)
                processing_time = time.time() - start_time
                
                # 응답 표시
                formatted_response = self.format_response(response)
                print(formatted_response)
                
                # 간단한 통계 표시
                print(f"\n 이번 세션 통계: 총 {self.system.system_stats['total_queries']}개 쿼리 처리")
                
            except KeyboardInterrupt:
                print("\n\n 중단되었습니다. 'exit'을 입력하여 정상 종료하세요.")
            except Exception as e:
                print(f"\n오류가 발생했습니다: {e}")
                print("계속 진행하려면 아무 키나 누르세요...")
    
    async def run_demo_queries(self):
        """데모 쿼리 실행"""
        demo_queries = [
            "금융소비자보호법이란 무엇인가요?",
            "멀티 에이전트 시스템의 아키텍처는 어떻게 설계하나요?",
            "최신 AI 기술 동향에 대해 알려주세요."
        ]
        
        print("\n데모 쿼리 실행:")
        for i, query in enumerate(demo_queries, 1):
            print(f"\n[{i}/{len(demo_queries)}] 처리 중: {query}")
            response = await self.system.process_user_query(query)
            
            print(f"답변:")
            print(f"{response['final_answer'][:200]}...")
            print(f"참여 에이전트: {', '.join(response['source_agents'])}")
    
    async def run_batch_test(self):
        """배치 테스트 실행"""
        test_queries = [
            "AI란 무엇인가요?",
            "블록체인 기술의 장점은?",
            "기계학습과 딥러닝의 차이점은?",
            "클라우드 컴퓨팅의 미래는?",
            "사이버 보안의 중요성은?"
        ]
        
        print(f"\n 배치 테스트 실행 ({len(test_queries)}개 쿼리):")
        
        start_time = time.time()
        results = await self.system.batch_process_queries(test_queries)
        total_time = time.time() - start_time
        
        print(f" 배치 처리 완료:")
        print(f"   총 처리 시간: {total_time:.2f}초")
        print(f"   평균 처리 시간: {total_time/len(test_queries):.2f}초/쿼리")
        
        successful = sum(1 for r in results if len(r.get('source_agents', [])) > 0)
        print(f"   성공률: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")

async def main():
    """메인 함수"""
    app = MultiAgentApp()
    
    print("\n🎮 실행 모드를 선택하세요:")
    print("1. 대화형 모드 (기본)")
    print("2. 데모 쿼리 실행")
    print("3. 배치 테스트")
    print("4. 시스템 상태만 확인")
    
    try:
        choice = input("\n선택 (1-4, 엔터=1): ").strip()
        
        if choice == "2":
            await app.run_demo_queries()
        elif choice == "3":
            await app.run_batch_test()
        elif choice == "4":
            await app.display_system_status()
        else:
            await app.run_interactive_mode()
            
    except KeyboardInterrupt:
        print("\n 프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"\n예기치 않은 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 