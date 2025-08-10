"""
관리자 에이전트 - 워커 에이전트들의 결과를 통합하여 최종 답변 생성
"""
import asyncio
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from statistics import mean

from llm_handler import LLMHandler
from worker_agents import WorkerAgentPool, AgentResponse
from memory_manager import MemoryManager
from feedback_system import FeedbackSystem

@dataclass
class FinalResponse:
    """최종 응답 데이터 클래스"""
    query: str
    final_answer: str
    source_agents: List[str]
    reasoning_process: str
    execution_time: float
    quality_metrics: Dict[str, Any]
    sources: List[Dict[str, Any]]

class ManagerAgent:
    """관리자 에이전트 - 워커 에이전트들의 결과를 통합하고 최종 답변 생성"""
    
    def __init__(self):
        # Manager Agent는 허깅페이스 모델 사용
        self.llm_handler = LLMHandler(
            model_name="microsoft/DialoGPT-large",
            temperature=0.3
        )
        self.worker_pool = WorkerAgentPool()
        self.memory_manager = MemoryManager(db_path="manager_memory.db")
        self.feedback_system = FeedbackSystem()
        
        # 응답 품질 평가 기준
        self.quality_thresholds = {
            "min_response_length": 50,
            "max_response_length": 2000,
            "consistency_threshold": 0.7
        }
    
    async def process_query(self, query: str) -> FinalResponse:
        """사용자 쿼리를 처리하고 최종 답변 생성"""
        start_time = time.time()
        
        try:
            # 1. 모든 워커 에이전트에게 쿼리 전달
            print(f"[ManagerAgent] 쿼리 처리 시작: {query}")
            worker_responses = await self.worker_pool.process_query_all_agents(query)
            
            # 2. 워커 응답 품질 평가
            quality_analysis = self._analyze_response_quality(worker_responses)
            
            # 3. 응답 일관성 검증
            consistency_analysis = self._analyze_consistency(worker_responses)
            
            # 4. 최고 품질 응답 선별
            best_responses = self._select_best_responses(worker_responses, quality_analysis)
            
            # 5. 최종 답변 생성
            final_answer = await self._generate_final_answer(
                query, 
                best_responses, 
                quality_analysis, 
                consistency_analysis
            )
            

            
            # 7. 추론 과정 생성
            reasoning_process = self._generate_reasoning_process(
                worker_responses, 
                quality_analysis, 
                consistency_analysis
            )
            
            # 8. 소스 통합
            all_sources = self._consolidate_sources(worker_responses)
            
            # 9. 품질 메트릭 생성
            quality_metrics = self._generate_quality_metrics(
                worker_responses, 
                quality_analysis, 
                consistency_analysis
            )
            
            # 10. 메모리에 저장
            self._save_to_memory(query, final_answer, worker_responses, quality_metrics)
            
            execution_time = time.time() - start_time
            
            return FinalResponse(
                query=query,
                final_answer=final_answer,
                source_agents=[resp.agent_id for resp in best_responses],
                reasoning_process=reasoning_process,
                execution_time=execution_time,
                quality_metrics=quality_metrics,
                sources=all_sources
            )
            
        except Exception as e:
            print(f"[ManagerAgent] 오류 발생: {e}")
            print(f"[ManagerAgent] 오류 타입: {type(e).__name__}")
            import traceback
            print(f"[ManagerAgent] 전체 트레이스백:")
            traceback.print_exc()
            execution_time = time.time() - start_time
            
            return FinalResponse(
                query=query,
                final_answer=f"처리 중 오류가 발생했습니다: {str(e)}",
                source_agents=[],
                reasoning_process=f"관리자 에이전트 오류: {str(e)}",
                execution_time=execution_time,
                quality_metrics={"error": str(e)},
                sources=[]
            )
    
    async def synthesize_agent_responses(self, query: str, refined_responses: List[AgentResponse]) -> Dict[str, Any]:
        """보완된 워커 에이전트 답변들을 종합 분석"""
        try:
            print(f"[ManagerAgent] 보완된 답변들 종합 분석 시작: {len(refined_responses)}개 응답")
            
            if not refined_responses:
                return {
                    "success": False,
                    "error": "분석할 보완된 응답이 없습니다",
                    "synthesis_summary": ""
                }
            
            # 1. 보완된 응답들의 품질 재평가
            quality_analysis = self._analyze_response_quality(refined_responses)
            
            # 2. 보완된 응답들 간의 일관성 검증
            consistency_analysis = self._analyze_consistency(refined_responses)
            
            # 3. 피드백 반영 효과 분석
            feedback_effectiveness = self._analyze_feedback_effectiveness(refined_responses)
            
            # 4. 종합 분석 리포트 생성
            synthesis_report = await self._generate_synthesis_report(
                query, 
                refined_responses, 
                quality_analysis, 
                consistency_analysis,
                feedback_effectiveness
            )
            
            # 5. 최종 통합 권장사항 생성
            integration_recommendations = self._generate_integration_recommendations(
                refined_responses, 
                quality_analysis
            )
            
            return {
                "success": True,
                "synthesis_summary": synthesis_report,
                "quality_analysis": quality_analysis,
                "consistency_analysis": consistency_analysis,
                "feedback_effectiveness": feedback_effectiveness,
                "integration_recommendations": integration_recommendations,
                "refined_responses_count": len(refined_responses),
                "synthesis_timestamp": time.time()
            }
            
        except Exception as e:
            print(f"[ManagerAgent] 종합 분석 실패: {e}")
            return {
                "success": False,
                "error": f"종합 분석 실패: {str(e)}",
                "synthesis_summary": ""
            }
    
    def _analyze_response_quality(self, responses: List[AgentResponse]) -> Dict[str, Any]:
        """워커 응답 품질 분석"""
        quality_analysis = {
            "individual_scores": {},
            "successful_responses": 0,
            "failed_responses": 0,
            "response_lengths": {},
            "execution_times": {}
        }
        
        successful_responses = [r for r in responses if r.success]
        failed_responses = [r for r in responses if not r.success]
        
        quality_analysis["successful_responses"] = len(successful_responses)
        quality_analysis["failed_responses"] = len(failed_responses)
        
        if successful_responses:
            # 개별 품질 점수 계산
            for response in successful_responses:
                quality_score = self._calculate_quality_score(response)
                quality_analysis["individual_scores"][response.agent_id] = quality_score
                quality_analysis["response_lengths"][response.agent_id] = len(response.response)
                quality_analysis["execution_times"][response.agent_id] = response.execution_time
            

        
        return quality_analysis
    
    def _calculate_quality_score(self, response: AgentResponse) -> float:
        """개별 응답의 품질 점수 계산"""
        score_factors = []
        
        # 응답 길이 (적절한 길이)
        response_length = len(response.response)
        if self.quality_thresholds["min_response_length"] <= response_length <= self.quality_thresholds["max_response_length"]:
            score_factors.append(0.8)
        else:
            score_factors.append(0.4)
        
        # 소스 품질
        if response.sources:
            high_quality_sources = len([s for s in response.sources if s.get("similarity", 0) > 0.7])
            source_score = min(high_quality_sources / len(response.sources), 1.0)
            score_factors.append(source_score)
        else:
            score_factors.append(0.3)
        
        # 실행 시간 (빠른 응답 선호)
        if response.execution_time < 5:
            score_factors.append(0.8)
        elif response.execution_time < 10:
            score_factors.append(0.6)
        else:
            score_factors.append(0.4)
        
        return sum(score_factors) / len(score_factors)
    
    def _analyze_consistency(self, responses: List[AgentResponse]) -> Dict[str, Any]:
        """응답 간 일관성 분석"""
        successful_responses = [r for r in responses if r.success and r.response]
        
        if len(successful_responses) < 2:
            return {
                "consistency_score": 1.0 if len(successful_responses) == 1 else 0.0,
                "agreement_level": "single_response" if len(successful_responses) == 1 else "no_responses",
                "conflicting_points": [],
                "common_themes": []
            }
        
        # 키워드 기반 일관성 분석
        all_keywords = []
        response_keywords = {}
        
        for response in successful_responses:
            keywords = self._extract_keywords(response.response)
            response_keywords[response.agent_id] = keywords
            all_keywords.extend(keywords)
        
        # 공통 키워드 찾기
        common_keywords = []
        for keyword in set(all_keywords):
            count = sum(1 for keywords in response_keywords.values() if keyword in keywords)
            if count >= len(successful_responses) * 0.5:  # 50% 이상 일치
                common_keywords.append(keyword)
        
        # 일관성 점수 계산
        consistency_score = len(common_keywords) / max(len(set(all_keywords)), 1)
        
        return {
            "consistency_score": min(consistency_score, 1.0),
            "agreement_level": self._determine_agreement_level(consistency_score),
            "common_themes": common_keywords[:10],  # 상위 10개
            "response_similarities": self._calculate_response_similarities(successful_responses)
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출 (간단한 구현)"""
        # 실제로는 더 정교한 키워드 추출 알고리즘 사용
        import re
        words = re.findall(r'\b\w{3,}\b', text.lower())
        # 한글 키워드 추출을 위한 간단한 처리
        korean_words = re.findall(r'[가-힣]{2,}', text)
        return list(set(words + korean_words))[:20]  # 상위 20개
    
    def _determine_agreement_level(self, consistency_score: float) -> str:
        """일관성 점수를 바탕으로 합의 수준 결정"""
        if consistency_score >= 0.8:
            return "high_agreement"
        elif consistency_score >= 0.6:
            return "moderate_agreement"
        elif consistency_score >= 0.4:
            return "low_agreement"
        else:
            return "conflicting"
    
    def _calculate_response_similarities(self, responses: List[AgentResponse]) -> Dict[str, float]:
        """응답 간 유사도 계산"""
        similarities = {}
        
        for i, resp1 in enumerate(responses):
            for j, resp2 in enumerate(responses[i+1:], i+1):
                # 간단한 Jaccard 유사도 계산
                words1 = set(self._extract_keywords(resp1.response))
                words2 = set(self._extract_keywords(resp2.response))
                
                if len(words1.union(words2)) > 0:
                    similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                else:
                    similarity = 0.0
                
                similarities[f"{resp1.agent_id}_vs_{resp2.agent_id}"] = similarity
        
        return similarities
    
    def _select_best_responses(self, 
                             responses: List[AgentResponse], 
                             quality_analysis: Dict[str, Any]) -> List[AgentResponse]:
        """최고 품질 응답 선별"""
        successful_responses = [r for r in responses if r.success]
        
        if not successful_responses:
            return []
        
        # 품질 점수로 정렬
        scored_responses = []
        for response in successful_responses:
            quality_score = quality_analysis["individual_scores"].get(response.agent_id, 0)
            scored_responses.append((response, quality_score))
        
        # 점수순으로 정렬
        scored_responses.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 응답들 중 임계값 이상만 선택
        best_responses = []
        for response, score in scored_responses:
            if score >= 0.5:
                best_responses.append(response)
        
        # 최소 1개는 반환 (가장 좋은 것)
        if not best_responses and scored_responses:
            best_responses = [scored_responses[0][0]]
        
        return best_responses
    
    async def _generate_final_answer(self, 
                                   query: str,
                                   best_responses: List[AgentResponse],
                                   quality_analysis: Dict[str, Any],
                                   consistency_analysis: Dict[str, Any]) -> str:
        """최종 답변 생성"""
        if not best_responses:
            return "죄송합니다. 현재 적절한 답변을 생성할 수 없습니다."
        
        # 최고 품질 응답이 1개인 경우
        if len(best_responses) == 1:
            return best_responses[0].response
        
        # 여러 응답을 통합하여 최종 답변 생성
        synthesis_prompt = f"""
# Role: 당신은 모든 에이전트가 가지고 있는 금융, 법률 ,일반상식에 대한 전문지식을 보유한 관리자입니다. 모든 AI 에이전트의 응답을 분석하고 종합하여, 최종 답변을 생성합니다. 또한, 대응 방안, 권리 보호 방안, 분쟁 해결 절차를 명확하고 신뢰성 있게 안내합니다.

# Action:
- 아래 사용자 질문과 각 에이전트의 응답, 일관성 분석 결과를 종합적으로 분석하고 핵심적인 사실, 대응 방안, 권리 보호 방안, 분쟁 헤결 절차를 포함한 통합된 최종 답변을 생성합니다.

# Constraints:
- 모든 에이전트의 응답을 종합적으로 고려하여 최종 답변을 생성합니다.
- 모든 에이전트의 응답을 균형있게 분석하여 최종 답변을 생성합니다.
- 정확하고 신뢰성 있는 정보를 우선시하며 불확실한 정보는 솔직하게 언급합니다.
- 공통된 내용은 확실하게 제시하고, 상충하는 내용은 균형있게 다룹니다.
- 모든 사람들이 알아들을 수 있게 명확하고 이해하기 쉬운 한국어로 답변합니다.
- 가독성이 높게 답변을 깔끔하고 일목요연하게 작성합니다.
- 불확실한 부분은 솔직하게 언급합니다.
- 아래의 명시된 출려 구조에 따라 각 섹션의 구체적인 내용을 반드시 포함합니다.

# Meta(일관성 분석 참고용):
- 합의 수준: {consistency_analysis.get('agreement_level', 'unknown')}
- 일관성 점수: {consistency_analysis.get('consistency_score', 0):.2f}
- 공통 주제: {', '.join(consistency_analysis.get('common_themes', [])[:5])}

# Context:
사용자 질문: {query}

제공된 응답들:
"""
        
        for idx, response in enumerate(best_responses, 1):
            synthesis_prompt += f"""
--- 에이전트 {response.agent_id} 응답 ---
{response.response}

"""
        synthesis_prompt += f"""
# Output:
1. 주요 해결 방안 및 분쟁 해결 절차
[구체적인 해결책과 조치 사항 그리고 권리 보호를 위한 구체적인 이행 절차, 구제 절차 및 방법]

2 추가 참고사항
[주의사항, 관련 기관 연락처, 추가 도움 등]

최종 답변:"""
        
        result = self.feedback_system.execute_with_feedback(
            self.llm_handler.get_response,
            synthesis_prompt,
            error_context="Manager agent final answer generation"
        )
        
        if result["success"]:
            return result["result"]
        else:
            # 통합 실패 시 최고 품질 응답 반환
            return best_responses[0].response
    

    
    def _generate_reasoning_process(self,
                                  worker_responses: List[AgentResponse],
                                  quality_analysis: Dict[str, Any],
                                  consistency_analysis: Dict[str, Any]) -> str:
        """추론 과정 생성"""
        reasoning_parts = []
        
        reasoning_parts.append("[ManagerAgent] 멀티 에이전트 처리 과정:")
        
        # 워커 에이전트 처리 결과
        successful_count = quality_analysis["successful_responses"]
        failed_count = quality_analysis["failed_responses"]
        reasoning_parts.append(f"- 성공한 에이전트: {successful_count}개, 실패한 에이전트: {failed_count}개")
        

        
        # 일관성 분석
        agreement_level = consistency_analysis.get("agreement_level", "unknown")
        consistency_score = consistency_analysis.get("consistency_score", 0)
        reasoning_parts.append(f"- 응답 일관성: {agreement_level} (점수: {consistency_score:.2f})")
        
        # 최종 결정 과정
        if successful_count > 0:
            reasoning_parts.append("- 품질 분석을 통해 최적 응답 선별 후 종합하여 최종 답변 생성")
        else:
            reasoning_parts.append("- 모든 에이전트 실패로 오류 응답 생성")
        
        return " ".join(reasoning_parts)
    
    def _consolidate_sources(self, responses: List[AgentResponse]) -> List[Dict[str, Any]]:
        """소스 통합 및 중복 제거"""
        all_sources = []
        seen_sources = set()
        
        for response in responses:
            if not response.success:
                continue
                
            for source in response.sources:
                # 중복 제거를 위한 식별자 생성
                source_id = source.get("content", "") + source.get("title", "")
                source_hash = hash(source_id)
                
                if source_hash not in seen_sources:
                    seen_sources.add(source_hash)
                    source_with_agent = source.copy()
                    source_with_agent["source_agent"] = response.agent_id
                    all_sources.append(source_with_agent)
        
        # 품질순으로 정렬 (유사도 기준)
        all_sources.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        return all_sources[:10]  # 상위 10개만 반환
    
    def _generate_quality_metrics(self,
                                worker_responses: List[AgentResponse],
                                quality_analysis: Dict[str, Any],
                                consistency_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """품질 메트릭 생성"""
        return {
            "total_agents": len(worker_responses),
            "successful_agents": quality_analysis["successful_responses"],
            "failed_agents": quality_analysis["failed_responses"],
            "consistency_score": consistency_analysis.get("consistency_score", 0),
            "agreement_level": consistency_analysis.get("agreement_level", "unknown"),
            "individual_scores": quality_analysis.get("individual_scores", {}),
            "execution_times": quality_analysis.get("execution_times", {}),
            "response_lengths": quality_analysis.get("response_lengths", {})
        }
    
    def _save_to_memory(self,
                       query: str,
                       final_answer: str,
                       worker_responses: List[AgentResponse],
                       quality_metrics: Dict[str, Any]):
        """메모리에 처리 결과 저장"""
        # 성공한 에이전트 응답만 저장
        successful_agents = [r.agent_id for r in worker_responses if r.success]
        
        self.memory_manager.save_interaction(
            user_query=query,
            agent_response=final_answer,
            tools_used=["multi_agent_processing"] + successful_agents,
            success=len(successful_agents) > 0
        )
        
        # 품질 패턴 학습
        pattern_data = {
            "agent_count": len(successful_agents),
            "consistency": quality_metrics.get("consistency_score", 0)
        }
        
        self.memory_manager.learn_pattern(
            pattern_type="multi_agent_quality",
            pattern_data=pattern_data,
            success=len(successful_agents) > 0
        )
    
    def _analyze_feedback_effectiveness(self, refined_responses: List[AgentResponse]) -> Dict[str, Any]:
        """피드백 반영 효과 분석"""
        try:
            effectiveness_score = 0.0
            refined_count = 0
            improvements = []
            
            for response in refined_responses:
                # 보완된 응답인지 확인 (응답 메타데이터 기반)
                if hasattr(response, 'is_refined') or 'is_refined' in str(response.reasoning):
                    refined_count += 1
                    # 응답 길이와 품질을 기반으로 개선도 평가
                    if len(response.response) > 100:  # 기본적인 품질 임계값
                        effectiveness_score += 1.0
                        improvements.append(f"{response.agent_id}: 피드백 반영하여 답변 보완됨")
            
            if refined_count > 0:
                effectiveness_score = effectiveness_score / refined_count
            
            return {
                "effectiveness_score": effectiveness_score,
                "refined_responses_count": refined_count,
                "total_responses_count": len(refined_responses),
                "improvement_rate": refined_count / len(refined_responses) if refined_responses else 0,
                "improvements": improvements
            }
            
        except Exception as e:
            return {
                "effectiveness_score": 0.0,
                "error": f"피드백 효과 분석 실패: {str(e)}"
            }
    
    async def _generate_synthesis_report(self, query: str, refined_responses: List[AgentResponse], 
                                       quality_analysis: Dict, consistency_analysis: Dict,
                                       feedback_effectiveness: Dict) -> str:
        """종합 분석 리포트 생성"""
        try:
            # 각 에이전트의 보완된 답변 요약
            agent_summaries = []
            for response in refined_responses:
                agent_summaries.append(
                    f"**{response.agent_id}**: {response.response[:200]}..."
                )
            
            synthesis_prompt = f"""
다음은 사용자 질문에 대한 여러 전문 에이전트들의 보완된 답변들입니다. 이들을 종합 분석하여 통찰력 있는 리포트를 작성하세요.

**사용자 질문**: {query}

**보완된 에이전트 답변들**:
{chr(10).join(agent_summaries)}

**품질 분석 결과**: 평균 품질 점수 {quality_analysis.get('average_quality_score', 0):.2f}
**일관성 분석 결과**: 일관성 점수 {consistency_analysis.get('consistency_score', 0):.2f}
**피드백 효과**: 개선률 {feedback_effectiveness.get('improvement_rate', 0)*100:.1f}%

다음 관점에서 종합 분석하세요:

1. **핵심 통찰**: 모든 답변을 통합했을 때 도출되는 핵심 인사이트
2. **상호 보완성**: 각 에이전트 답변이 서로를 어떻게 보완하는지
3. **신뢰도 평가**: 전체적인 답변의 신뢰도와 근거 강도
4. **실용적 가치**: 사용자에게 제공할 수 있는 실질적 도움
5. **개선 효과**: 피드백을 통한 답변 품질 향상 정도

간결하면서도 포괄적인 분석을 제공하세요.
"""
            
            synthesis_result = self.llm_handler.get_response(synthesis_prompt, max_tokens=2048)
            return synthesis_result
            
        except Exception as e:
            return f"종합 분석 리포트 생성 실패: {str(e)}"
    
    def _generate_integration_recommendations(self, refined_responses: List[AgentResponse], 
                                            quality_analysis: Dict) -> List[str]:
        """통합 권장사항 생성"""
        recommendations = []
        
        try:
            # 고품질 응답들 식별
            high_quality_agents = []
            for response in refined_responses:
                # 품질 점수가 높은 응답들 (임계값: 0.7)
                if len(response.response) > 100 and response.success:
                    high_quality_agents.append(response.agent_id)
            
            if high_quality_agents:
                recommendations.append(f"우수 답변 에이전트: {', '.join(high_quality_agents)}")
            
            # 응답 완성도 기반 권장사항
            total_sources = sum(len(r.sources) for r in refined_responses)
            if total_sources > 5:
                recommendations.append("풍부한 출처 기반으로 신뢰성 높은 답변 제공 가능")
            
            # 일관성 기반 권장사항
            if quality_analysis.get('average_quality_score', 0) > 0.7:
                recommendations.append("에이전트 간 피드백을 통해 답변 품질이 크게 향상됨")
            
            # 피드백 효과 권장사항
            refined_count = sum(1 for r in refined_responses if 'is_refined' in str(r.reasoning))
            if refined_count > 0:
                recommendations.append(f"{refined_count}개 답변이 상호 피드백을 통해 보완됨")
            
        except Exception as e:
            recommendations.append(f"권장사항 생성 중 오류: {str(e)}")
        
        return recommendations if recommendations else ["기본 통합 권장사항이 적용됩니다"]
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            "manager_status": "active",
            "worker_pool_status": self.worker_pool.get_agent_status(),
            "memory_status": self.memory_manager.get_session_context(),
            "feedback_status": self.feedback_system.get_error_analysis(),
            "quality_thresholds": self.quality_thresholds
        } 