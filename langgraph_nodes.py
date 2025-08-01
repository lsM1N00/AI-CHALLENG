"""
LangGraph 멀티 에이전트 시스템의 노드 함수들
"""
import asyncio
import time
from typing import Dict, List, Any
from statistics import mean

from langgraph_agent_state import AgentState, NodeResult
from worker_agents import WorkerAgentPool, AgentResponse
from manager_agent import ManagerAgent


class LangGraphNodes:
    """LangGraph 워크플로우의 노드 함수들을 포함하는 클래스"""
    
    def __init__(self):
        self.worker_pool = WorkerAgentPool()
        self.manager = ManagerAgent()
    
    async def analyze_query_node(self, state: AgentState) -> dict:
        """쿼리 분석 노드"""
        try:
            print(f"[QueryAnalysis] 쿼리 분석 시작: {state.query}")
            
            # 쿼리 복잡도 분석
            analysis = self._analyze_query_complexity(state.query)
            
            print(f"[QueryAnalysis] 분석 완료. 복잡도: {analysis.get('complexity_score', 0.0):.2f}")
            
            return {
                "query_analysis": analysis,
                "complexity_score": analysis.get("complexity_score", 0.0),
                "estimated_processing_time": analysis.get("estimated_processing_time", 10.0),
                "next_step": "execute_agents"
            }
            
        except Exception as e:
            print(f"[QueryAnalysis] 오류: {e}")
            return {
                "success": False,
                "error_message": f"쿼리 분석 실패: {str(e)}",
                "should_continue": False,
                "execution_time": 0
            }
    
    async def execute_legal_agent_node(self, state: AgentState) -> dict:
        """법률 전문 에이전트 실행 노드"""
        try:
            print(f"[LegalAgent] 법률 에이전트 실행 시작")
            legal_agent = self.worker_pool.agents["legal"]
            response = await legal_agent.process_query(state.query)
            
            legal_response = {
                "agent_id": response.agent_id,
                "response": response.response,
                "sources": response.sources,
                "reasoning": response.reasoning,
                "execution_time": response.execution_time,
                "success": response.success,
                "error": response.error
            }
            
            print(f"[LegalAgent] 실행 완료. 성공: {response.success}")
            return {"legal_response": legal_response}
            
        except Exception as e:
            print(f"[LegalAgent] 오류: {e}")
            return {
                "legal_response": {
                    "agent_id": "LegalExpert",
                    "response": "",
                    "sources": [],
                    "reasoning": f"실행 오류: {str(e)}",
                    "execution_time": 0,
                    "success": False,
                    "error": str(e)
                }
            }
    
    async def execute_technical_agent_node(self, state: AgentState) -> dict:
        """기술 분석 에이전트 실행 노드"""
        try:
            print(f"[TechnicalAgent] 기술 분석 에이전트 실행 시작")
            technical_agent = self.worker_pool.agents["technical"]
            response = await technical_agent.process_query(state.query)
            
            technical_response = {
                "agent_id": response.agent_id,
                "response": response.response,
                "sources": response.sources,
                "reasoning": response.reasoning,
                "execution_time": response.execution_time,
                "success": response.success,
                "error": response.error
            }
            
            print(f"[TechnicalAgent] 실행 완료. 성공: {response.success}")
            return {"technical_response": technical_response}
            
        except Exception as e:
            print(f"[TechnicalAgent] 오류: {e}")
            return {
                "technical_response": {
                    "agent_id": "TechnicalAnalyst",
                    "response": "",
                    "sources": [],
                    "reasoning": f"실행 오류: {str(e)}",
                    "execution_time": 0,
                    "success": False,
                    "error": str(e)
                }
            }
    
    async def execute_general_agent_node(self, state: AgentState) -> dict:
        """일반 지식 에이전트 실행 노드"""
        try:
            print(f"[GeneralAgent] 일반 지식 에이전트 실행 시작")
            general_agent = self.worker_pool.agents["general"]
            response = await general_agent.process_query(state.query)
            
            general_response = {
                "agent_id": response.agent_id,
                "response": response.response,
                "sources": response.sources,
                "reasoning": response.reasoning,
                "execution_time": response.execution_time,
                "success": response.success,
                "error": response.error
            }
            
            print(f"[GeneralAgent] 실행 완료. 성공: {response.success}")
            return {"general_response": general_response}
            
        except Exception as e:
            print(f"[GeneralAgent] 오류: {e}")
            return {
                "general_response": {
                    "agent_id": "GeneralKnowledge",
                    "response": "",
                    "sources": [],
                    "reasoning": f"실행 오류: {str(e)}",
                    "execution_time": 0,
                    "success": False,
                    "error": str(e)
                }
            }
    
    async def cross_feedback_node(self, state: AgentState) -> dict:
        """Worker 에이전트들이 서로의 답변에 피드백을 제공하는 노드"""
        try:
            print(f"[CrossFeedback] Worker 에이전트 간 피드백 시작")
            
            # 모든 에이전트 응답 수집
            agent_responses = {
                "legal": state.legal_response,
                "technical": state.technical_response, 
                "general": state.general_response
            }
            
            # 각 에이전트가 다른 에이전트들의 답변에 피드백 제공
            feedback_results = {}
            
            for current_agent, current_response in agent_responses.items():
                if not current_response or not current_response.get("success"):
                    continue
                    
                # 다른 에이전트들의 답변 수집
                other_responses = {k: v for k, v in agent_responses.items() if k != current_agent and v and v.get("success")}
                
                if other_responses:
                    feedback = await self._generate_cross_feedback(
                        current_agent, 
                        current_response, 
                        other_responses, 
                        state.query
                    )
                    feedback_results[current_agent] = feedback
            
            print(f"[CrossFeedback] 피드백 완료. 생성된 피드백: {len(feedback_results)}개")
            
            return {
                "cross_feedback": feedback_results,
                "next_step": "refine_responses"
            }
            
        except Exception as e:
            print(f"[CrossFeedback] 오류: {e}")
            return {
                "cross_feedback": {},
                "error_message": f"피드백 생성 실패: {str(e)}"
            }
    
    async def refine_responses_node(self, state: AgentState) -> dict:
        """피드백을 바탕으로 각 에이전트가 답변을 보완하는 노드"""
        try:
            print(f"[RefineResponses] 답변 보완 시작")
            
            # 피드백 정보 수집
            cross_feedback = getattr(state, 'cross_feedback', {})
            if not cross_feedback:
                print(f"[RefineResponses] 피드백 정보 없음, 원본 답변 유지")
                return {
                    "refined_legal_response": state.legal_response,
                    "refined_technical_response": state.technical_response,
                    "refined_general_response": state.general_response,
                    "next_step": "manager_synthesis"
                }
            
            # 각 에이전트의 답변을 피드백 기반으로 보완
            refined_responses = {}
            
            agent_map = {
                "legal": state.legal_response,
                "technical": state.technical_response,
                "general": state.general_response
            }
            
            for agent_type, original_response in agent_map.items():
                if not original_response or not original_response.get("success"):
                    refined_responses[f"refined_{agent_type}_response"] = original_response
                    continue
                
                agent_feedback = cross_feedback.get(agent_type, {})
                if agent_feedback:
                    refined_response = await self._refine_response_with_feedback(
                        agent_type,
                        original_response,
                        agent_feedback,
                        state.query
                    )
                    refined_responses[f"refined_{agent_type}_response"] = refined_response
                else:
                    refined_responses[f"refined_{agent_type}_response"] = original_response
            
            print(f"[RefineResponses] 답변 보완 완료")
            
            refined_responses["next_step"] = "manager_synthesis"
            return refined_responses
            
        except Exception as e:
            print(f"[RefineResponses] 오류: {e}")
            return {
                "refined_legal_response": state.legal_response,
                "refined_technical_response": state.technical_response,
                "refined_general_response": state.general_response,
                "error_message": f"답변 보완 실패: {str(e)}",
                "next_step": "manager_synthesis"
            }
    
    async def manager_synthesis_node(self, state: AgentState) -> dict:
        """Manager 에이전트가 보완된 답변들을 종합하는 노드"""
        try:
            print(f"[ManagerSynthesis] Manager 에이전트 종합 분석 시작")
            
            # 보완된 응답들 수집
            refined_responses = []
            
            for response_key in ["refined_legal_response", "refined_technical_response", "refined_general_response"]:
                response_data = getattr(state, response_key, None)
                if response_data and response_data.get("success"):
                    agent_response = AgentResponse(
                        agent_id=response_data["agent_id"],
                        response=response_data["response"],
                        sources=response_data["sources"],
                        reasoning=response_data["reasoning"],
                        execution_time=response_data["execution_time"],
                        success=response_data["success"],
                        error=response_data.get("error")
                    )
                    refined_responses.append(agent_response)
            
            # Manager가 보완된 답변들을 종합하여 최종 분석
            manager_analysis = await self.manager.synthesize_agent_responses(
                state.query, 
                refined_responses
            )
            
            print(f"[ManagerSynthesis] Manager 종합 분석 완료")
            
            return {
                "manager_synthesis": manager_analysis,
                "consolidated_responses": refined_responses,
                "next_step": "generate_final_answer"
            }
            
        except Exception as e:
            print(f"[ManagerSynthesis] 오류: {e}")
            return {
                "manager_synthesis": {},
                "error_message": f"Manager 종합 분석 실패: {str(e)}",
                "next_step": "generate_final_answer"
            }
    
    async def quality_analysis_node(self, state: AgentState) -> dict:
        """응답 품질 분석 노드"""
        try:
            print(f"[QualityAnalysis] 품질 분석 시작")
            
            # 모든 에이전트 응답 수집
            responses = []
            for response_data in [state.legal_response, state.technical_response, state.general_response]:
                if response_data:
                    # Dict를 AgentResponse 객체로 변환
                    agent_response = AgentResponse(
                        agent_id=response_data["agent_id"],
                        response=response_data["response"],
                        sources=response_data["sources"],
                        reasoning=response_data["reasoning"],
                        execution_time=response_data["execution_time"],
                        success=response_data["success"],
                        error=response_data.get("error")
                    )
                    responses.append(agent_response)
            
            # 품질 분석 수행
            quality_analysis = self.manager._analyze_response_quality(responses)
            consistency_analysis = self.manager._analyze_consistency(responses)
            best_responses = self.manager._select_best_responses(responses, quality_analysis)
            
            best_responses_data = [
                {
                    "agent_id": resp.agent_id,
                    "response": resp.response,
                    "sources": resp.sources,
                    "reasoning": resp.reasoning,
                    "execution_time": resp.execution_time,
                    "success": resp.success
                }
                for resp in best_responses
            ]
            
            print(f"[QualityAnalysis] 분석 완료. 선별된 응답: {len(best_responses)}개")
            
            return {
                "quality_analysis": quality_analysis,
                "consistency_analysis": consistency_analysis,
                "best_responses": best_responses_data,
                "next_step": "generate_final_answer"
            }
            
        except Exception as e:
            print(f"[QualityAnalysis] 오류: {e}")
            return {
                "success": False,
                "error_message": f"품질 분석 실패: {str(e)}",
                "should_continue": False
            }
    
    async def generate_final_answer_node(self, state: AgentState) -> dict:
        """최종 답변 생성 노드"""
        try:
            print(f"[FinalAnswer] 최종 답변 생성 시작")
            
            if not state.best_responses:
                final_answer = "죄송합니다. 현재 적절한 답변을 생성할 수 없습니다."
                reasoning_process = "선별된 응답이 없어 기본 오류 메시지 반환"
                consolidated_sources = []
                quality_metrics = {}
            else:
                # AgentResponse 객체로 변환
                best_agent_responses = []
                for resp_data in state.best_responses:
                    agent_response = AgentResponse(
                        agent_id=resp_data["agent_id"],
                        response=resp_data["response"],
                        sources=resp_data["sources"],
                        reasoning=resp_data["reasoning"],
                        execution_time=resp_data["execution_time"],
                        success=resp_data["success"]
                    )
                    best_agent_responses.append(agent_response)
                
                # 최종 답변 생성
                final_answer = await self.manager._generate_final_answer(
                    state.query,
                    best_agent_responses,
                    state.quality_analysis,
                    state.consistency_analysis
                )
                
                # 추론 과정 생성
                all_responses = []
                for response_data in [state.legal_response, state.technical_response, state.general_response]:
                    if response_data:
                        agent_response = AgentResponse(
                            agent_id=response_data["agent_id"],
                            response=response_data["response"],
                            sources=response_data["sources"],
                            reasoning=response_data["reasoning"],
                            execution_time=response_data["execution_time"],
                            success=response_data["success"],
                            error=response_data.get("error")
                        )
                        all_responses.append(agent_response)
                
                reasoning_process = self.manager._generate_reasoning_process(
                    all_responses,
                    state.quality_analysis,
                    state.consistency_analysis
                )
                
                # 소스 통합
                consolidated_sources = self.manager._consolidate_sources(all_responses)
                
                # 품질 메트릭 생성
                quality_metrics = self.manager._generate_quality_metrics(
                    all_responses,
                    state.quality_analysis,
                    state.consistency_analysis
                )
            
            # 시스템 메타데이터 생성
            system_metadata = {
                "query_analysis": state.query_analysis,
                "system_version": "2.0.0-langgraph",
                "processing_timestamp": time.time(),
                "workflow_type": "langgraph_multi_agent"
            }
            
            print(f"[FinalAnswer] 최종 답변 생성 완료")
            
            return {
                "final_answer": final_answer,
                "reasoning_process": reasoning_process,
                "consolidated_sources": consolidated_sources,
                "quality_metrics": quality_metrics,
                "system_metadata": system_metadata,
                "success": True,
                "execution_time": time.time() - state.execution_start_time,
                "should_continue": False,
                # 에이전트 응답 정보도 명시적으로 포함
                "legal_response": state.legal_response,
                "technical_response": state.technical_response,
                "general_response": state.general_response
            }
            
        except Exception as e:
            print(f"[FinalAnswer] 오류: {e}")
            return {
                "success": False,
                "error_message": f"최종 답변 생성 실패: {str(e)}",
                "should_continue": False,
                "execution_time": time.time() - state.execution_start_time
            }
    
    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """쿼리 복잡도 분석 (기존 로직 재사용)"""
        try:
            # 간단한 쿼리 분석
            analysis_result = self._simple_query_analysis(query)
            
            # 추가 복잡도 분석
            complexity_factors = {
                "length": len(query),
                "word_count": len(query.split()),
                "has_question_mark": "?" in query or "？" in query,
                "has_multiple_sentences": len([s for s in query.split('.') if s.strip()]) > 1,
                "requires_legal_expertise": any(keyword in query.lower() for keyword in ["법", "조항", "규정", "법률"]),
                "requires_technical_expertise": any(keyword in query.lower() for keyword in ["기술", "시스템", "구현", "개발"]),
                "requires_general_knowledge": analysis_result in ["Web Search", "None"]
            }
            
            # 복잡도 점수 계산
            complexity_score = 0
            if complexity_factors["word_count"] > 10:
                complexity_score += 0.3
            if complexity_factors["has_multiple_sentences"]:
                complexity_score += 0.2
            if complexity_factors["requires_legal_expertise"]:
                complexity_score += 0.3
            if complexity_factors["requires_technical_expertise"]:
                complexity_score += 0.3
            
            return {
                "original_analysis": analysis_result,
                "complexity_factors": complexity_factors,
                "complexity_score": min(complexity_score, 1.0),
                "estimated_processing_time": self._estimate_processing_time(complexity_score)
            }
            
        except Exception as e:
            print(f"쿼리 분석 오류: {e}")
            return {
                "original_analysis": "Unknown",
                "complexity_factors": {},
                "complexity_score": 0.5,
                "estimated_processing_time": 10
            }
    
    def _simple_query_analysis(self, query: str) -> str:
        """간단한 쿼리 분석"""
        query_lower = query.lower()
        
        # 법률 관련 키워드
        legal_keywords = ["법", "조항", "규정", "법률", "판례", "사례", "금융소비자보호", "소비자보호"]
        if any(keyword in query_lower for keyword in legal_keywords):
            return "RAG"
        
        # 기술 관련 키워드
        tech_keywords = ["분석", "판례", "사례", "FAQ", "대응 절차 안내", "소비자보호", "민원분석", "보호방안", "분쟁해결절차"]
        if any(keyword in query_lower for keyword in tech_keywords):
            return "Web Search"
        
        # 질문이 있는 경우
        if "?" in query or "？" in query:
            return "Both"
        
        # 기본값
        return "Web Search"
    
    def _estimate_processing_time(self, complexity_score: float) -> float:
        """복잡도 기반 처리 시간 추정"""
        base_time = 5  # 기본 5초
        complexity_factor = complexity_score * 10  # 복잡도에 따른 추가 시간
        return base_time + complexity_factor 

    async def _generate_cross_feedback(self, current_agent: str, current_response: dict, other_responses: dict, query: str) -> dict:
        """에이전트가 다른 에이전트들의 답변에 피드백을 제공"""
        try:
            # 현재 에이전트 가져오기
            agent = self.worker_pool.agents.get(current_agent)
            if not agent:
                return {"error": f"에이전트 {current_agent}를 찾을 수 없습니다"}
            
            # 다른 에이전트들의 답변 요약
            other_responses_summary = ""
            for agent_type, response_data in other_responses.items():
                other_responses_summary += f"\n--- {agent_type.upper()} 에이전트 답변 ---\n"
                other_responses_summary += f"{response_data.get('response', '')[:500]}...\n"
                other_responses_summary += f"출처: {', '.join(response_data.get('sources', [])[:3])}\n"
            
            # 피드백 생성 프롬프트
            feedback_prompt = f"""
# Role: 당신은 전문 분야 관점에서 다른 에이전트들의 답변을 평가하고 개선 방향을 제시(피드백)하는 전문가입니다.

# Action:
- 아래의 사용자 질문과 다른 에이전트들의 답변입니다. 당신의 전문 분야 관점에서 이들 답변에 대한 건설적인 피드백을 제공하세요.

# Constraints:
- 각 피드백 항목은 명확하고 근거에 기반하시오.
- 불필요한 칭찬이나 비논리적 주장은 피하고 구체적인 제안을 하시오.
- 다른 답변을 왜곡하거난 과도하게 비판하지 마시오.
- 당신의 피드백은 다른 Agent가 답변을 개선하는 데 도운이 되어야 합니다.

# Context:
- 사용자 질문: {query}
- 다른 에이전트들의 답변:{other_responses_summary}
- 당신의 전문 분야: {current_agent} Agent

# Output:
- 다음 관점에서 피드백을 제공하세요:
1. 보완점: 다른 답변에서 놓친 중요한 정보나 관점
2. 정확성: factual 오류나 개선이 필요한 부분
3. 연결점: 당신의 전문 분야와 연관된 추가 정보
4. 통합 제안: 더 나은 통합 답변을 위한 제안

각 항목별로 구체적이고 실용적인 피드백을 제공하세요.
"""
            
            # LLM을 통해 피드백 생성
            feedback_response = agent.llm_handler.get_response(feedback_prompt, max_tokens=2048)
            
            return {
                "feedback_provider": current_agent,
                "feedback_content": feedback_response,
                "reviewed_agents": list(other_responses.keys()),
                "generation_time": time.time()
            }
            
        except Exception as e:
            return {
                "error": f"피드백 생성 실패: {str(e)}",
                "feedback_provider": current_agent
            }
    
    async def _refine_response_with_feedback(self, agent_type: str, original_response: dict, feedback_data: dict, query: str) -> dict:
        """피드백을 바탕으로 답변을 보완"""
        try:
            # 해당 에이전트 가져오기
            agent = self.worker_pool.agents.get(agent_type)
            if not agent:
                return original_response
            
            # 피드백 내용 추출
            feedback_content = feedback_data.get("feedback_content", "")
            if not feedback_content:
                return original_response
            
            # 답변 보완 프롬프트
            refinement_prompt = f"""
# Role: 당신은 전문 분야에 능숙한 전문가이며, 당신은 이전에 제공한 답변에 대해 피드백을 받고, 그 피드백을 바탕으로 답변을 보완하는 전문가입니다.

# Action:
- 아래는 당신이 이전에 제공한 답변과 다른 에이전트로부터 받은 피드백입니다. 이전 답변과 피드백을 검토하고 종합하여 보다 더 정확하고 완성도 높은 답변으로 보안하시오.

# Constraints:
- 피드백을 적극 반영하되, 당신의 전문 분야 관점은 유지하세요.
- 피드백에서 말한 누락된 정보를 추가하시오.
- 부정확하거나 오해 소지가 있는 부분은 수정하시오.
- 다른 관점 또는 추가된 정보는 자연스럽게 통합하시오.
- 원본 답변의 핵심과 강점은 유지하시오.
- 더 정확하고 포괄적인 답변을 제공하시오.
- 수정 이유나 설명 없이 최종 보완된 답변만 출력하시오.

# Context:

- 사용자 질문: {query}

- 당신의 이전 답변: {original_response.get('response', '')}

- 다른 에이전트들의 피드백: {feedback_content}

# Output:
- 보완된 답변만 제공하고, 수정 과정에 대한 설명은 생략하세요.
"""
            
            # 보완된 답변 생성
            refined_content = agent.llm_handler.get_response(refinement_prompt, max_tokens=4096)
            
            # 보완된 응답 객체 생성
            refined_response = original_response.copy()
            refined_response.update({
                "response": refined_content,
                "reasoning": f"{original_response.get('reasoning', '')} [피드백 반영하여 보완됨]",
                "is_refined": True,
                "feedback_incorporated": True,
                "refinement_time": time.time()
            })
            
            return refined_response
            
        except Exception as e:
            print(f"[RefineResponse] {agent_type} 답변 보완 실패: {e}")
            return original_response 