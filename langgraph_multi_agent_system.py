"""
LangGraph 기반 멀티 에이전트 시스템
"""
import asyncio
import time
from typing import Dict, List, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from langgraph_agent_state import AgentState
from langgraph_nodes import LangGraphNodes
from memory_manager import MemoryManager
from feedback_system import FeedbackSystem


class LangGraphMultiAgentSystem:
    """LangGraph 기반 멀티 에이전트 시스템"""
    
    def __init__(self):
        # 핵심 컴포넌트 초기화
        self.nodes = LangGraphNodes()
        self.system_memory = MemoryManager(db_path="system_memory.db")
        self.system_feedback = FeedbackSystem()
        
        # 워크플로우 그래프 생성
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
        
        # 시스템 상태
        self.system_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0,
            "system_health": "healthy"
        }
        
        self.is_initialized = True
        print("[LangGraphMultiAgentSystem] 시스템 초기화 완료")
    
    def _create_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 생성"""
        # StateGraph 생성
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("analyze_query", self.nodes.analyze_query_node)
        workflow.add_node("execute_legal_agent", self.nodes.execute_legal_agent_node)
        workflow.add_node("execute_technical_agent", self.nodes.execute_technical_agent_node)
        workflow.add_node("execute_general_agent", self.nodes.execute_general_agent_node)
        workflow.add_node("cross_feedback", self.nodes.cross_feedback_node)
        workflow.add_node("refine_responses", self.nodes.refine_responses_node)
        workflow.add_node("manager_synthesis", self.nodes.manager_synthesis_node)
        workflow.add_node("quality_analysis", self.nodes.quality_analysis_node)
        workflow.add_node("generate_final_answer", self.nodes.generate_final_answer_node)
        
        # 새로운 워크플로우 구조 정의
        workflow.set_entry_point("analyze_query")
        
        # 1단계: 쿼리 분석 후 모든 에이전트 병렬 실행 (1차 응답 생성)
        workflow.add_edge("analyze_query", "execute_legal_agent")
        workflow.add_edge("analyze_query", "execute_technical_agent")
        workflow.add_edge("analyze_query", "execute_general_agent")
        
        # 2단계: 모든 에이전트 완료 후 상호 피드백
        workflow.add_edge("execute_legal_agent", "cross_feedback")
        workflow.add_edge("execute_technical_agent", "cross_feedback")
        workflow.add_edge("execute_general_agent", "cross_feedback")
        
        # 3단계: 피드백을 바탕으로 답변 보완
        workflow.add_edge("cross_feedback", "refine_responses")
        
        # 4단계: Manager가 보완된 답변들을 종합
        workflow.add_edge("refine_responses", "manager_synthesis")
        
        # 5단계: 품질 분석
        workflow.add_edge("manager_synthesis", "quality_analysis")
        
        # 6단계: 최종 답변 생성
        workflow.add_edge("quality_analysis", "generate_final_answer")
        
        # 최종 답변 후 종료
        workflow.add_edge("generate_final_answer", END)
        
        return workflow
    
    async def process_user_query(self, user_query: str) -> Dict[str, Any]:
        """사용자 쿼리를 LangGraph 워크플로우로 처리"""
        if not self.is_initialized:
            return self._create_error_response("시스템이 초기화되지 않았습니다.")
        
        start_time = time.time()
        self.system_stats["total_queries"] += 1
        
        try:
            print(f"[LangGraphMultiAgentSystem] LangGraph 워크플로우 시작: {user_query}")
            
            # 1. 시스템 상태 점검
            system_health = self._check_system_health()
            if not system_health["healthy"]:
                return self._create_error_response(
                    "시스템 상태가 불안정합니다.",
                    {"health_status": system_health}
                )
            
            # 2. 초기 상태 생성
            initial_state = AgentState(
                query=user_query,
                original_query=user_query,
                messages=[HumanMessage(content=user_query)]
            )
            
            # 3. LangGraph 워크플로우 실행
            print("[LangGraphMultiAgentSystem] 워크플로우 실행 중...")
            final_state = None
            
            # 상태를 순차적으로 업데이트하며 실행
            async for state in self.app.astream(initial_state):
                final_state = state
                # 중간 상태 로깅 - state는 딕셔너리 형태
                if isinstance(state, dict) and 'next_step' in state:
                    print(f"[LangGraphMultiAgentSystem] 현재 단계: {state.get('next_step', 'unknown')}")
            
            if final_state is None:
                raise Exception("워크플로우 실행 결과를 받지 못했습니다")
            
            # 4. 최종 상태에서 결과 추출
            # LangGraph는 노드별로 중첩된 상태를 반환하므로 모든 노드 결과를 병합
            if isinstance(final_state, dict):
                merged_state = {}
                
                # 모든 노드의 결과를 순차적으로 병합
                node_results = [
                    'analyze_query',
                    'execute_legal_agent', 
                    'execute_technical_agent',
                    'execute_general_agent',
                    'cross_feedback',
                    'refine_responses',
                    'manager_synthesis',
                    'quality_analysis',
                    'generate_final_answer'
                ]
                
                # 각 노드의 결과를 확인하고 병합
                for node_name in node_results:
                    if node_name in final_state:
                        node_result = final_state[node_name]
                        if isinstance(node_result, dict):
                            merged_state.update(node_result)
                
                # 원본 상태도 포함 (초기 query 등)
                for key, value in final_state.items():
                    if key not in node_results:  # 노드 결과가 아닌 직접 상태값들
                        merged_state[key] = value
                
                # 에이전트 응답이 누락된 경우 AgentState에서 직접 추출
                if not any(key.endswith('_response') for key in merged_state.keys()):
                    # LangGraph의 실제 상태는 일반적으로 __end__ 키에 저장됨
                    if '__end__' in final_state and hasattr(final_state['__end__'], '__dict__'):
                        agent_state = final_state['__end__']
                        if hasattr(agent_state, 'legal_response'):
                            merged_state['legal_response'] = agent_state.legal_response
                        if hasattr(agent_state, 'technical_response'):
                            merged_state['technical_response'] = agent_state.technical_response
                        if hasattr(agent_state, 'general_response'):
                            merged_state['general_response'] = agent_state.general_response
                
                result_state = merged_state
            else:
                result_state = final_state
            
            # 5. 응답 후처리
            execution_time = time.time() - start_time
            processed_response = self._post_process_response(result_state, execution_time)
            
            # 6. 시스템 통계 업데이트
            success = processed_response.get('success', False)
            self._update_system_stats(execution_time, success=success)
            
            # 7. 시스템 메모리에 저장
            self._save_system_interaction(user_query, processed_response, execution_time)
            
            return processed_response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_system_stats(execution_time, success=False)
            
            error_response = self._create_error_response(
                f"LangGraph 워크플로우 처리 중 오류 발생: {str(e)}",
                {
                    "error_type": type(e).__name__,
                    "execution_time": execution_time
                }
            )
            
            print(f"[LangGraphMultiAgentSystem] 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return error_response
    
    def _post_process_response(self, final_state, execution_time: float) -> Dict[str, Any]:
        """응답 후처리 및 포맷팅"""
        # 상태에서 데이터 추출 - 딕셔너리 또는 AgentState 객체 모두 처리
        if isinstance(final_state, dict):
            response_data = dict(final_state)
        elif hasattr(final_state, 'to_dict'):
            response_data = final_state.to_dict()
        else:
            response_data = {}
        
        # 기본값 설정
        response_data.setdefault("query", "")
        response_data.setdefault("final_answer", "")
        response_data.setdefault("reasoning_process", "")
        response_data.setdefault("success", False)
        response_data.setdefault("error_message", "")
        response_data.setdefault("consolidated_sources", [])
        response_data.setdefault("quality_metrics", {})
        
        # 실행 시간 업데이트
        response_data["execution_time"] = execution_time
        
        # 시스템 메타데이터 가져오기
        system_metadata = response_data.get('system_metadata', {})
        
        # 추가 메타데이터 포함
        response_data.update({
            "system_metadata": {
                **system_metadata,
                "system_version": "2.0.0-langgraph",
                "processing_timestamp": time.time(),
                "total_system_queries": self.system_stats["total_queries"],
                "workflow_type": "langgraph_parallel_agents"
            },
            "response_quality": self._assess_response_quality(final_state),
            "recommendations": self._generate_recommendations(final_state)
        })
        
        return response_data
    
    def _assess_response_quality(self, state) -> Dict[str, Any]:
        """응답 품질 평가"""
        quality_assessment = {
            "overall_score": 0,
            "factors": {},
            "quality_level": "unknown"
        }
        
        try:
            factors = []
            
            # 상태에서 값 추출 (딕셔너리 또는 객체 모두 처리)
            def get_value(key, default=None):
                if isinstance(state, dict):
                    return state.get(key, default)
                else:
                    return getattr(state, key, default)
            
            # 응답 길이 적절성
            final_answer = get_value('final_answer', '')
            response_length = len(final_answer)
            if 50 <= response_length <= 1000:
                length_score = 0.8
            elif 1000 < response_length <= 2000:
                length_score = 0.6
            else:
                length_score = 0.4
            factors.append(length_score)
            quality_assessment["factors"]["length_appropriateness"] = length_score
            
            # 소스 활용도
            consolidated_sources = get_value('consolidated_sources', [])
            source_count = len(consolidated_sources)
            source_score = min(source_count / 5, 1.0) if source_count > 0 else 0.3
            factors.append(source_score)
            quality_assessment["factors"]["source_utilization"] = source_score
            
            # 처리 시간 효율성
            execution_time = get_value('execution_time', 0)
            if execution_time < 10:
                time_score = 0.9
            elif execution_time < 20:
                time_score = 0.7
            else:
                time_score = 0.5
            factors.append(time_score)
            quality_assessment["factors"]["time_efficiency"] = time_score
            
            # 에이전트 성공률
            legal_response = get_value('legal_response', {})
            technical_response = get_value('technical_response', {})
            general_response = get_value('general_response', {})
            
            successful_agents = sum(1 for resp in [legal_response, technical_response, general_response] 
                                  if resp and resp.get("success", False))
            agent_success_score = successful_agents / 3 if successful_agents > 0 else 0
            factors.append(agent_success_score)
            quality_assessment["factors"]["agent_success_rate"] = agent_success_score
            
            # 전체 점수 계산
            overall_score = sum(factors) / len(factors)
            quality_assessment["overall_score"] = overall_score
            
            # 품질 레벨 결정
            if overall_score >= 0.8:
                quality_assessment["quality_level"] = "excellent"
            elif overall_score >= 0.6:
                quality_assessment["quality_level"] = "good"
            elif overall_score >= 0.4:
                quality_assessment["quality_level"] = "fair"
            else:
                quality_assessment["quality_level"] = "poor"
                
        except Exception as e:
            quality_assessment["error"] = str(e)
        
        return quality_assessment
    
    def _generate_recommendations(self, state) -> List[str]:
        """사용자를 위한 추천 사항 생성"""
        recommendations = []
        
        try:
            # 상태에서 값 추출 (딕셔너리 또는 객체 모두 처리)
            def get_value(key, default=None):
                if isinstance(state, dict):
                    return state.get(key, default)
                else:
                    return getattr(state, key, default)
            
            # 소스 기반 추천
            consolidated_sources = get_value('consolidated_sources', [])
            if len(consolidated_sources) == 0:
                recommendations.append("관련 문서를 찾지 못했습니다. 다른 키워드로 질문해보세요.")
            elif len(consolidated_sources) < 3:
                recommendations.append("제한된 소스에서 답변을 생성했습니다. 더 자세한 정보가 필요하면 질문을 세분화해보세요.")
            
            # 복잡도 기반 추천
            complexity_score = get_value('complexity_score', 0)
            if complexity_score > 0.7:
                recommendations.append("복잡한 질문입니다. 여러 부분으로 나누어 질문하면 더 정확한 답변을 받을 수 있습니다.")
            
            # 에이전트 성공률 기반 추천
            legal_response = get_value('legal_response', {})
            technical_response = get_value('technical_response', {})
            general_response = get_value('general_response', {})
            
            successful_agents = sum(1 for resp in [legal_response, technical_response, general_response] 
                                  if resp and resp.get("success", False))
            if successful_agents < 2:
                recommendations.append("일부 전문 에이전트가 실패했습니다. 질문을 더 구체적으로 하시거나 잠시 후 다시 시도해보세요.")
            
            # 전문성 기반 추천
            query_analysis = get_value('query_analysis', {})
            complexity_factors = query_analysis.get("complexity_factors", {})
            if complexity_factors.get("requires_legal_expertise"):
                recommendations.append("법률 관련 질문입니다. 정확한 법적 조언이 필요하다면 전문가와 상담하세요.")
            
            if complexity_factors.get("requires_technical_expertise"):
                recommendations.append("기술적 질문입니다. 구체적인 구현이 필요하다면 해당 분야 전문가에게 문의하세요.")
                
        except Exception as e:
            recommendations.append("추천 사항 생성 중 오류가 발생했습니다.")
        
        return recommendations[:5]  # 최대 5개 추천사항
    
    def _check_system_health(self) -> Dict[str, Any]:
        """시스템 건강 상태 점검"""
        health_status = {
            "healthy": True,
            "issues": [],
            "performance_metrics": {}
        }
        
        try:
            # 최근 성공률 확인
            total_queries = self.system_stats["total_queries"]
            success_rate = 1.0  # 기본값
            
            if total_queries >= 5:
                success_rate = self.system_stats["successful_queries"] / total_queries
                if success_rate < 0.7:
                    health_status["issues"].append("낮은 성공률")
                    if success_rate < 0.5:
                        health_status["healthy"] = False
            elif total_queries > 0:
                success_rate = self.system_stats["successful_queries"] / total_queries
            
            # 평균 응답 시간 확인 - 임계값을 300초로 완화
            avg_response_time = self.system_stats["average_response_time"]
            if avg_response_time > 120:
                health_status["issues"].append("높은 응답 시간")
                if avg_response_time > 300:  # 60초에서 300초로 완화
                    health_status["healthy"] = False
            
            health_status["performance_metrics"] = {
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "total_queries": total_queries
            }
            
        except Exception as e:
            print(f"시스템 상태 점검 실패: {e}")
            health_status["healthy"] = False
            health_status["issues"].append(f"시스템 점검 오류: {str(e)}")
        
        return health_status
    
    def _update_system_stats(self, execution_time: float, success: bool):
        """시스템 통계 업데이트"""
        if success:
            self.system_stats["successful_queries"] += 1
        else:
            self.system_stats["failed_queries"] += 1
        
        # 평균 응답 시간 업데이트
        total_queries = self.system_stats["total_queries"]
        current_avg = self.system_stats["average_response_time"]
        new_avg = ((current_avg * (total_queries - 1)) + execution_time) / total_queries
        self.system_stats["average_response_time"] = new_avg
        
        # 시스템 건강도 업데이트
        success_rate = self.system_stats["successful_queries"] / total_queries
        if success_rate >= 0.8 and new_avg < 20:
            self.system_stats["system_health"] = "excellent"
        elif success_rate >= 0.6 and new_avg < 30:
            self.system_stats["system_health"] = "good"
        elif success_rate >= 0.4:
            self.system_stats["system_health"] = "fair"
        else:
            self.system_stats["system_health"] = "poor"
    
    def _save_system_interaction(self, query: str, response: Dict[str, Any], execution_time: float):
        """시스템 레벨 상호작용 저장"""
        try:
            self.system_memory.save_interaction(
                user_query=query,
                agent_response=response.get("final_answer", ""),
                tools_used=["langgraph_multi_agent"],
                success=response.get("success", False)
            )
            
            # 시스템 성능 패턴 학습
            pattern_data = {
                "execution_time": execution_time,
                "complexity_score": response.get("system_metadata", {}).get("query_analysis", {}).get("complexity_score", 0),
                "workflow_type": "langgraph"
            }
            
            self.system_memory.learn_pattern(
                pattern_type="langgraph_performance",
                pattern_data=pattern_data,
                success=response.get("success", False)
            )
            
        except Exception as e:
            print(f"시스템 상호작용 저장 오류: {e}")
    
    def _create_error_response(self, error_message: str, additional_data: Dict = None) -> Dict[str, Any]:
        """오류 응답 생성"""
        error_response = {
            "query": "",
            "final_answer": error_message,
            "reasoning_process": f"LangGraph 시스템 오류: {error_message}",
            "execution_time": 0,
            "success": False,
            "error_message": error_message,
            "quality_metrics": {"error": True},
            "consolidated_sources": [],
            "system_metadata": {
                "error": True,
                "error_message": error_message,
                "system_version": "2.0.0-langgraph",
                "processing_timestamp": time.time(),
                "workflow_type": "langgraph_error"
            },
            "response_quality": {
                "overall_score": 0,
                "quality_level": "error"
            },
            "recommendations": ["시스템 관리자에게 문의하거나 잠시 후 다시 시도해보세요."]
        }
        
        if additional_data:
            error_response["system_metadata"].update(additional_data)
        
        return error_response
    
    def get_system_status(self) -> Dict[str, Any]:
        """전체 시스템 상태 반환"""
        return {
            "system_stats": self.system_stats,
            "system_health": self._check_system_health(),
            "workflow_info": {
                "nodes": list(self.workflow.nodes.keys()),
                "edges": len(self.workflow.edges),
                "type": "langgraph_state_graph"
            },
            "memory_status": self.system_memory.get_session_context(),
            "is_initialized": self.is_initialized
        }
    
    def reset_system(self):
        """시스템 리셋"""
        self.system_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0,
            "system_health": "healthy"
        }
        
        self.system_memory.start_new_session()
        print("[LangGraphMultiAgentSystem] 시스템 리셋 완료")
    
    async def batch_process_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """배치 쿼리 처리"""
        print(f"[LangGraphMultiAgentSystem] 배치 처리 시작: {len(queries)}개 쿼리")
        
        tasks = []
        for query in queries:
            task = asyncio.create_task(self.process_user_query(query))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        print(f"[LangGraphMultiAgentSystem] 배치 처리 완료")
        return results 