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
        """FAQ, 민원 사례 분석 에이전트 실행 노드"""
        try:
            print(f"[TechnicalAgent] FAQ, 민원 사례 분석 에이전트 실행 시작")
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
        """금융 지식 에이전트 실행 노드"""
        try:
            print(f"[GeneralAgent] 금융 지식 에이전트 실행 시작")
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
        """Manager 에이전트가 보완된 답변들을 종합하고 도구 호출 여부를 분석하는 노드"""
        try:
            print(f"[ManagerSynthesis] Manager 에이전트 종합 분석 및 도구 호출 분석 시작")
            
            # 1. 도구 호출 필요성 분석
            tool_analysis = await self._analyze_tool_calling_needs(state.query, state)
            
            # 2. 보완된 응답들 수집
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
            
            # 3. Manager가 보완된 답변들을 종합하여 최종 분석
            manager_analysis = await self.manager.synthesize_agent_responses(
                state.query, 
                refined_responses
            )
            
            print(f"[ManagerSynthesis] Manager 종합 분석 완료. 도구 호출: {tool_analysis['needs_tool']}")
            
            return {
                "manager_synthesis": manager_analysis,
                "tool_analysis": tool_analysis,
                "consolidated_responses": refined_responses,
                "next_step": "generate_final_answer"
            }
            
        except Exception as e:
            print(f"[ManagerSynthesis] 오류: {e}")
            return {
                "manager_synthesis": {},
                "tool_analysis": {"needs_tool": False, "tool_type": "none", "reason": "오류 발생"},
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

    async def _analyze_tool_calling_needs(self, query: str, state: AgentState) -> dict:
        """SLM을 사용하여 사용자 쿼리를 지능적으로 분석하고 도구 호출 필요성 판단"""
        try:
            print(f"[ToolAnalysis] SLM 기반 도구 호출 필요성 분석: {query}")
            
            # 1. SLM을 사용한 지능적 분석
            tool_analysis_result = await self._slm_analyze_tool_needs(query, state)
            
            # 2. 분석 결과 로깅
            print(f"[ToolAnalysis] SLM 분석 결과:")
            print(f"  - 도구 호출 필요: {tool_analysis_result['needs_tool']}")
            print(f"  - 도구 유형: {tool_analysis_result['tool_type']}")
            print(f"  - 판단 근거: {tool_analysis_result['reason']}")
            print(f"  - 신뢰도: {tool_analysis_result.get('confidence', 0.0):.2f}")
            
            return tool_analysis_result
            
        except Exception as e:
            print(f"[ToolAnalysis] SLM 분석 오류: {e}")
            # SLM 분석 실패 시 기본 규칙 기반 분석으로 폴백
            return await self._fallback_rule_based_analysis(query, state)
    
    async def _slm_analyze_tool_needs(self, query: str, state: AgentState) -> dict:
        """Manager 에이전트 모델을 사용한 도구 호출 필요성 분석"""
        try:
            # Manager 에이전트 모델 사용
            if self.manager and hasattr(self.manager, 'llm'):
                # SLM 프롬프트 구성
                slm_prompt = self._create_tool_analysis_prompt(query, state)
                
                # Manager 에이전트의 LLM으로 분석
                analysis_response = await self.manager.llm.get_response(slm_prompt)
                
                # SLM 응답 파싱
                parsed_analysis = self._parse_slm_tool_analysis(analysis_response)
                
                # 기본 정보 추가
                parsed_analysis.update({
                    "analysis_method": "Manager Agent Model",
                    "analysis_timestamp": time.time(),
                    "query": query,
                    "complexity_score": getattr(state, 'complexity_score', 0.0),
                    "word_count": len(query.split()),
                    "has_question_mark": "?" in query or "？" in query
                })
                
                return parsed_analysis
            else:
                raise Exception("Manager 에이전트 모델을 사용할 수 없습니다")
                
        except Exception as e:
            print(f"[ManagerAnalysis] Manager 에이전트 분석 실패: {e}")
            raise e
    
    def _create_tool_analysis_prompt(self, query: str, state: AgentState) -> str:
        """도구 호출 분석을 위한 SLM 프롬프트 생성"""
        complexity_score = getattr(state, 'complexity_score', 0.0)
        word_count = len(query.split())
        
        prompt = f"""
# Role: 당신은 금융분쟁 해결 AI 시스템의 도구 호출 분석 전문가입니다.

# Task: 주어진 사용자 질문을 분석하여 어떤 도구를 사용해야 하는지 판단하세요.

# Context:
- 사용자 질문: "{query}"
- 질문 길이: {word_count}개 단어
- 복잡도 점수: {complexity_score:.2f} (0.0~1.0, 높을수록 복잡)

# Available Tools:
1. **direct_response**: 단순 대화, 인사, 간단한 질문에 직접 응답
2. **document_retriever**: 전문적 금융/법률 질문, 구체적인 절차/방법 질문에 문서 검색

# Analysis Criteria:
- **단순 대화/인사**: "안녕하세요", "고마워요", "어떻게 해요?" 등
- **전문 질문**: "대출 분쟁 해결 방법", "보험금 청구 절차", "법적 책임" 등
- **구체적 절차**: "어떤 서류가 필요해요?", "언제까지 신고해야 해요?" 등
- **복잡한 상황**: 여러 조건이 포함된 복합적인 질문

# Output Format (JSON):
{{
    "needs_tool": true/false,
    "tool_type": "direct_response" or "document_retriever",
    "reason": "판단 근거를 간단명료하게 설명",
    "confidence": 0.0~1.0 (판단 신뢰도),
    "analysis_details": {{
        "query_category": "질문 카테고리 (인사/일반질문/전문질문/절차질문)",
        "complexity_level": "복잡도 수준 (낮음/보통/높음)",
        "requires_expertise": true/false,
        "suggested_approach": "제안하는 접근 방법"
    }}
}}

# Instructions:
1. 질문의 내용과 맥락을 정확히 파악하세요
2. 단순한 대화인지 전문적인 정보가 필요한지 판단하세요
3. JSON 형식으로 정확하게 응답하세요
4. 판단 근거를 명확하게 제시하세요

사용자 질문: "{query}"
"""
        return prompt
    
    def _parse_slm_tool_analysis(self, slm_response: str) -> dict:
        """SLM 응답을 파싱하여 도구 호출 분석 결과 추출"""
        try:
            # JSON 응답 추출 시도
            import json
            import re
            
            # JSON 블록 찾기
            json_match = re.search(r'\{.*\}', slm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis = json.loads(json_str)
                
                # 필수 필드 검증 및 기본값 설정
                return {
                    "needs_tool": analysis.get("needs_tool", False),
                    "tool_type": analysis.get("tool_type", "direct_response"),
                    "reason": analysis.get("reason", "SLM 분석 결과"),
                    "confidence": analysis.get("confidence", 0.8),
                    "analysis_details": analysis.get("analysis_details", {}),
                    "raw_slm_response": slm_response
                }
            else:
                # JSON이 없는 경우 텍스트 분석
                return self._fallback_text_analysis(slm_response)
                
        except Exception as e:
            print(f"[SLMParsing] SLM 응답 파싱 실패: {e}")
            return self._fallback_text_analysis(slm_response)
    
    def _fallback_text_analysis(self, slm_response: str) -> dict:
        """SLM 응답 파싱 실패 시 텍스트 기반 분석"""
        response_lower = slm_response.lower()
        
        # 키워드 기반 간단 분석
        if any(keyword in response_lower for keyword in ["document", "검색", "문서", "retriever"]):
            return {
                "needs_tool": True,
                "tool_type": "document_retriever",
                "reason": "SLM이 문서 검색 필요로 판단",
                "confidence": 0.6,
                "analysis_details": {"query_category": "전문질문"},
                "raw_slm_response": slm_response
            }
        elif any(keyword in response_lower for keyword in ["direct", "직접", "응답", "대화"]):
            return {
                "needs_tool": False,
                "tool_type": "direct_response",
                "reason": "SLM이 직접 응답으로 판단",
                "confidence": 0.6,
                "analysis_details": {"query_category": "일반질문"},
                "raw_slm_response": slm_response
            }
        else:
            return {
                "needs_tool": False,
                "tool_type": "direct_response",
                "reason": "SLM 응답 파싱 실패로 기본값 사용",
                "confidence": 0.3,
                "analysis_details": {"query_category": "분석실패"},
                "raw_slm_response": slm_response
            }
    
    async def _fallback_rule_based_analysis(self, query: str, state: AgentState) -> dict:
        """SLM 분석 실패 시 규칙 기반 분석으로 폴백"""
        print(f"[FallbackAnalysis] 규칙 기반 분석으로 폴백")
        
        query_lower = query.lower()
        complexity_score = getattr(state, 'complexity_score', 0.0)
        word_count = len(query.split())
        has_question_mark = "?" in query or "？" in query
        
        # 단순 대화 판단
        simple_keywords = ["안녕", "고마워", "좋아", "어떻게", "무엇", "언제", "어디서"]
        if any(keyword in query_lower for keyword in simple_keywords):
            if word_count <= 8 and complexity_score < 0.3:
                return {
                    "needs_tool": False,
                    "tool_type": "direct_response",
                    "reason": "규칙 기반: 단순 대화/질문",
                    "confidence": 0.5,
                    "analysis_method": "Rule-based Fallback",
                    "analysis_timestamp": time.time(),
                    "query": query,
                    "complexity_score": complexity_score,
                    "word_count": word_count,
                    "has_question_mark": has_question_mark
                }
        
        # 전문 질문 판단
        expert_keywords = ["법", "대출", "보험", "분쟁", "절차", "방법", "책임"]
        if any(keyword in query_lower for keyword in expert_keywords):
            return {
                "needs_tool": True,
                "tool_type": "document_retriever",
                "reason": "규칙 기반: 전문적 질문",
                "confidence": 0.5,
                "analysis_method": "Rule-based Fallback",
                "analysis_timestamp": time.time(),
                "query": query,
                "complexity_score": complexity_score,
                "word_count": word_count,
                "has_question_mark": has_question_mark
            }
        
        # 기본값
        return {
            "needs_tool": False,
            "tool_type": "direct_response",
            "reason": "규칙 기반: 기본값 (직접 응답)",
            "confidence": 0.3,
            "analysis_method": "Rule-based Fallback",
            "analysis_timestamp": time.time(),
            "query": query,
            "complexity_score": complexity_score,
            "word_count": word_count,
            "has_question_mark": has_question_mark
        } 