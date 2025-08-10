"""
LangGraph 멀티 에이전트 시스템 테스트
"""
import asyncio
import pytest
import time
from typing import Dict, Any

from langgraph_multi_agent_system import LangGraphMultiAgentSystem
from langgraph_agent_state import AgentState


class TestLangGraphSystem:
    """LangGraph 시스템 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.system = LangGraphMultiAgentSystem()
    
    @pytest.mark.asyncio
    async def test_system_initialization(self):
        """시스템 초기화 테스트"""
        assert self.system.is_initialized == True
        assert self.system.app is not None
        assert self.system.workflow is not None
        
        # 워크플로우 구조 확인
        nodes = list(self.system.workflow.nodes.keys())
        expected_nodes = [
            "analyze_query",
            "execute_legal_agent", 
            "execute_technical_agent",
            "execute_general_agent",
            "quality_analysis",
            "generate_final_answer"
        ]
        
        for node in expected_nodes:
            assert node in nodes, f"노드 {node}가 워크플로우에 없습니다"
    
    @pytest.mark.asyncio
    async def test_simple_query_processing(self):
        """간단한 쿼리 처리 테스트"""
        query = "금융소비자보호법이란 무엇인가요?"
        
        start_time = time.time()
        result = await self.system.process_user_query(query)
        execution_time = time.time() - start_time
        
        # 기본 응답 구조 확인
        assert isinstance(result, dict)
        assert "query" in result or "final_answer" in result
        assert "success" in result
        assert "execution_time" in result
        assert "system_metadata" in result
        
        # 실행 시간 확인 (30초 이내)
        assert execution_time < 30, f"실행 시간이 너무 깁니다: {execution_time}초"
        
        print(f"✅ 쿼리 처리 성공 - 실행 시간: {execution_time:.2f}초")
        print(f"✅ 성공 상태: {result.get('success', False)}")
        
        if result.get('success', False):
            assert len(result.get('final_answer', '')) > 0, "최종 답변이 비어있습니다"
            print(f"✅ 답변 길이: {len(result.get('final_answer', ''))}자")
    
    @pytest.mark.asyncio
    async def test_complex_query_processing(self):
        """복잡한 쿼리 처리 테스트"""
        query = "은행에서 대출을 부당하게 거절당했을 때 금융감독원에 신고하는 절차와 필요한 서류는 무엇인가요?"
        
        result = await self.system.process_user_query(query)
        
        assert isinstance(result, dict)
        
        # 복잡한 쿼리의 경우 더 긴 응답 기대
        if result.get('success', False):
            answer_length = len(result.get('final_answer', ''))
            assert answer_length > 100, f"복잡한 쿼리에 대한 답변이 너무 짧습니다: {answer_length}자"
            
            # 소스 활용 확인
            sources = result.get('consolidated_sources', [])
            print(f"✅ 활용된 소스 수: {len(sources)}")
            
            # 품질 메트릭 확인
            quality = result.get('response_quality', {})
            print(f"✅ 응답 품질: {quality.get('quality_level', 'unknown')} ({quality.get('overall_score', 0):.2f})")
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """배치 처리 테스트"""
        queries = [
            "금융소비자보호법이란?",
            "대환대출 조건은?",
            "금융감독원 신고 방법은?"
        ]
        
        start_time = time.time()
        results = await self.system.batch_process_queries(queries)
        total_time = time.time() - start_time
        
        assert len(results) == len(queries), "배치 처리 결과 수가 맞지 않습니다"
        
        # 각 결과 확인
        successful_results = 0
        for i, result in enumerate(results):
            assert isinstance(result, dict), f"결과 {i}가 딕셔너리가 아닙니다"
            if result.get('success', False):
                successful_results += 1
        
        print(f"✅ 배치 처리 완료 - 총 시간: {total_time:.2f}초")
        print(f"✅ 성공률: {successful_results}/{len(queries)}")
        print(f"✅ 평균 처리 시간: {total_time/len(queries):.2f}초")
        
        # 병렬 처리 효율성 확인 (순차 처리보다 빨라야 함)
        avg_time_per_query = total_time / len(queries)
        assert avg_time_per_query < 15, f"배치 처리가 너무 느립니다: {avg_time_per_query:.2f}초/쿼리"
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """오류 처리 테스트"""
        # 빈 쿼리
        result = await self.system.process_user_query("")
        assert isinstance(result, dict)
        
        # 매우 긴 쿼리
        long_query = "테스트 " * 1000
        result = await self.system.process_user_query(long_query)
        assert isinstance(result, dict)
        
        print("✅ 오류 처리 테스트 완료")
    
    def test_system_status(self):
        """시스템 상태 확인 테스트"""
        status = self.system.get_system_status()
        
        assert isinstance(status, dict)
        assert "system_stats" in status
        assert "system_health" in status
        assert "workflow_info" in status
        assert "is_initialized" in status
        
        # 워크플로우 정보 확인
        workflow_info = status["workflow_info"]
        assert "nodes" in workflow_info
        assert "type" in workflow_info
        assert workflow_info["type"] == "langgraph_state_graph"
        
        print("✅ 시스템 상태 확인 완료")
        print(f"✅ 워크플로우 노드 수: {len(workflow_info.get('nodes', []))}")
    
    def test_system_reset(self):
        """시스템 리셋 테스트"""
        # 초기 상태 확인
        initial_stats = self.system.system_stats.copy()
        
        # 일부 통계 변경
        self.system.system_stats["total_queries"] = 10
        self.system.system_stats["successful_queries"] = 8
        
        # 리셋 실행
        self.system.reset_system()
        
        # 리셋 후 상태 확인
        reset_stats = self.system.system_stats
        assert reset_stats["total_queries"] == 0
        assert reset_stats["successful_queries"] == 0
        assert reset_stats["failed_queries"] == 0
        assert reset_stats["system_health"] == "healthy"
        
        print("✅ 시스템 리셋 테스트 완료")


@pytest.mark.asyncio
async def test_workflow_components():
    """워크플로우 컴포넌트 개별 테스트"""
    from langgraph_nodes import LangGraphNodes
    
    nodes = LangGraphNodes()
    
    # 초기 상태 생성
    state = AgentState(
        query="테스트 쿼리입니다",
        original_query="테스트 쿼리입니다"
    )
    
    # 쿼리 분석 노드 테스트
    analyzed_state = await nodes.analyze_query_node(state)
    assert analyzed_state.complexity_score >= 0
    assert len(analyzed_state.query_analysis) > 0
    
    print("✅ 워크플로우 컴포넌트 테스트 완료")


def run_performance_test():
    """성능 테스트 실행"""
    async def performance_test():
        system = LangGraphMultiAgentSystem()
        
        test_queries = [
            "금융소비자보호법 위반 신고 절차",
            "대환대출 조건과 필요 서류",
            "은행 부당 대출 거절 대응 방안",
            "금융감독원 분쟁조정 신청 방법"
        ]
        
        print("🚀 성능 테스트 시작...")
        
        # 개별 쿼리 성능 테스트
        for i, query in enumerate(test_queries, 1):
            start_time = time.time()
            result = await system.process_user_query(query)
            exec_time = time.time() - start_time
            
            status = "✅" if result.get('success', False) else "❌"
            print(f"{status} 쿼리 {i}: {exec_time:.2f}초")
        
        # 배치 성능 테스트
        print("\n🔄 배치 처리 성능 테스트...")
        start_time = time.time()
        batch_results = await system.batch_process_queries(test_queries)
        batch_time = time.time() - start_time
        
        successful = sum(1 for r in batch_results if r.get('success', False))
        print(f"📊 배치 결과: {successful}/{len(test_queries)} 성공")
        print(f"⏱️ 배치 시간: {batch_time:.2f}초")
        print(f"⚡ 평균 시간: {batch_time/len(test_queries):.2f}초/쿼리")
    
    asyncio.run(performance_test())


if __name__ == "__main__":
    print("🧪 LangGraph 시스템 테스트 실행")
    
    # 성능 테스트 실행
    run_performance_test()
    
    print("\n🔬 상세 테스트를 실행하려면 pytest를 사용하세요:")
    print("pytest test_langgraph_system.py -v") 