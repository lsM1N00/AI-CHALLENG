import asyncio
import time
from typing import Dict, List, Any, Optional
import json
from dataclasses import asdict

from manager_agent import ManagerAgent, FinalResponse
from worker_agents import WorkerAgentPool
from memory_manager import MemoryManager
from feedback_system import FeedbackSystem

class MultiAgentSystem:
    """멀티 에이전트 시스템 오케스트레이터"""
    
    def __init__(self):
        # 핵심 컴포넌트 초기화
        self.manager_agent = ManagerAgent()
        self.system_memory = MemoryManager(db_path="system_memory.db")
        self.system_feedback = FeedbackSystem()
        
        # 시스템 상태
        self.system_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0,
            "system_health": "healthy"
        }
        
        self.is_initialized = True
        print("[MultiAgentSystem] 시스템 초기화 완료")
    
    async def process_user_query(self, user_query: str) -> Dict[str, Any]:
        """사용자 쿼리를 멀티 에이전트 시스템으로 처리"""
        if not self.is_initialized:
            return self._create_error_response("시스템이 초기화되지 않았습니다.")
        
        start_time = time.time()
        self.system_stats["total_queries"] += 1
        
        try:
            print(f"[MultiAgentSystem] 쿼리 분석 시작: {user_query}")
            
            # 1. 쿼리 사전 분석
            query_analysis = self._analyze_query_complexity(user_query)
            
            # 2. 시스템 상태 점검
            system_health = self._check_system_health()
            if not system_health["healthy"]:
                return self._create_error_response(
                    "시스템 상태가 불안정합니다.",
                    {"health_status": system_health}
                )
            
            # 3. 관리자 에이전트에게 처리 위임
            final_response = await self.manager_agent.process_query(user_query)
            
            # 4. 응답 후처리
            processed_response = self._post_process_response(final_response, query_analysis)
            
            # 5. 시스템 통계 업데이트
            execution_time = time.time() - start_time
            self._update_system_stats(execution_time, success=True)
            
            # 6. 시스템 메모리에 저장
            self._save_system_interaction(user_query, processed_response, execution_time)
            
            return processed_response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_system_stats(execution_time, success=False)
            
            error_response = self._create_error_response(
                f"시스템 처리 중 오류 발생: {str(e)}",
                {
                    "error_type": type(e).__name__,
                    "execution_time": execution_time
                }
            )
            
            print(f"[MultiAgentSystem] 오류 발생: {e}")
            return error_response
    
    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """쿼리 복잡도 분석"""
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
    
    def _estimate_processing_time(self, complexity_score: float) -> float:
        """복잡도 기반 처리 시간 추정"""
        base_time = 5  # 기본 5초
        complexity_factor = complexity_score * 10  # 복잡도에 따른 추가 시간
        return base_time + complexity_factor
    
    def _simple_query_analysis(self, query: str) -> str:
        """간단한 쿼리 분석"""
        query_lower = query.lower()
        
        # 법률 관련 키워드
        legal_keywords = ["법", "조항", "규정", "법률", "금융소비자보호", "소비자보호"]
        if any(keyword in query_lower for keyword in legal_keywords):
            return "RAG"
        
        # 기술 관련 키워드
        tech_keywords = ["기술", "시스템", "구현", "개발", "아키텍처", "코드"]
        if any(keyword in query_lower for keyword in tech_keywords):
            return "Web Search"
        
        # 질문이 있는 경우
        if "?" in query or "？" in query:
            return "Both"
        
        # 기본값
        return "Web Search"
    
    def _check_system_health(self) -> Dict[str, Any]:
        """시스템 건강 상태 점검"""
        health_status = {
            "healthy": True,
            "issues": [],
            "performance_metrics": {}
        }
        
        try:
            # 1. 관리자 에이전트 상태 확인
            print("[DEBUG] 관리자 에이전트 상태 확인 중...")
            manager_status = self.manager_agent.get_system_status()
            print(f"[DEBUG] 관리자 에이전트 상태: {manager_status}")
            
            # 2. 최근 성공률 확인 (최소 5개 쿼리 이후부터)
            total_queries = self.system_stats["total_queries"]
            success_rate = 1.0  # 기본값
            
            if total_queries >= 5:  # 최소 5개 쿼리 처리 후부터 성공률 체크
                success_rate = self.system_stats["successful_queries"] / total_queries
                if success_rate < 0.7:  # 성공률 70% 미만
                    health_status["issues"].append("낮은 성공률")
                    if success_rate < 0.5:
                        health_status["healthy"] = False
            elif total_queries > 0:
                success_rate = self.system_stats["successful_queries"] / total_queries
            
            # 3. 평균 응답 시간 확인
            avg_response_time = self.system_stats["average_response_time"]
            if avg_response_time > 30:  # 30초 초과
                health_status["issues"].append("높은 응답 시간")
                if avg_response_time > 60:
                    health_status["healthy"] = False
            
            # 4. 메모리 사용량 확인 (간단한 구현)
            try:
                memory_context = self.system_memory.get_session_context()
                recent_interactions = len(memory_context.get("recent_interactions", []))
                if recent_interactions > 100:  # 단기 메모리 과부하
                    health_status["issues"].append("메모리 과부하")
            except Exception:
                health_status["issues"].append("메모리 시스템 오류")
            
            health_status["performance_metrics"] = {
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "total_queries": total_queries
            }
            
        except Exception as e:
            print(f"[DEBUG] 시스템 상태 점검 실패: {e}")
            print(f"[DEBUG] 오류 타입: {type(e).__name__}")
            import traceback
            print(f"[DEBUG] 전체 트레이스백:")
            traceback.print_exc()
            health_status["healthy"] = False
            health_status["issues"].append(f"시스템 점검 오류: {str(e)}")
        
        return health_status
    
    def _post_process_response(self, 
                             final_response: FinalResponse, 
                             query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """응답 후처리 및 포맷팅"""
        response_data = asdict(final_response)
        
        # 추가 메타데이터 포함
        response_data.update({
            "system_metadata": {
                "query_analysis": query_analysis,
                "system_version": "1.0.0",
                "processing_timestamp": time.time(),
                "total_system_queries": self.system_stats["total_queries"]
            },
            "response_quality": self._assess_response_quality(final_response),
            "recommendations": self._generate_recommendations(final_response, query_analysis)
        })
        
        return response_data
    
    def _assess_response_quality(self, response: FinalResponse) -> Dict[str, Any]:
        """응답 품질 평가"""
        quality_assessment = {
            "overall_score": 0,
            "factors": {},
            "quality_level": "unknown"
        }
        
        try:
            factors = []
            

            
            # 응답 길이 적절성
            response_length = len(response.final_answer)
            if 50 <= response_length <= 1000:
                length_score = 0.8
            elif 1000 < response_length <= 2000:
                length_score = 0.6
            else:
                length_score = 0.4
            factors.append(length_score)
            quality_assessment["factors"]["length_appropriateness"] = length_score
            
            # 소스 활용도
            source_count = len(response.sources)
            source_score = min(source_count / 5, 1.0) if source_count > 0 else 0.3
            factors.append(source_score)
            quality_assessment["factors"]["source_utilization"] = source_score
            
            # 처리 시간 효율성
            execution_time = response.execution_time
            if execution_time < 10:
                time_score = 0.9
            elif execution_time < 20:
                time_score = 0.7
            else:
                time_score = 0.5
            factors.append(time_score)
            quality_assessment["factors"]["time_efficiency"] = time_score
            
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
    
    def _generate_recommendations(self, 
                                response: FinalResponse, 
                                query_analysis: Dict[str, Any]) -> List[str]:
        """사용자를 위한 추천 사항 생성"""
        recommendations = []
        
        try:

            
            # 소스 기반 추천
            if len(response.sources) == 0:
                recommendations.append("관련 문서를 찾지 못했습니다. 다른 키워드로 질문해보세요.")
            elif len(response.sources) < 3:
                recommendations.append("제한된 소스에서 답변을 생성했습니다. 더 자세한 정보가 필요하면 질문을 세분화해보세요.")
            
            # 복잡도 기반 추천
            complexity_score = query_analysis.get("complexity_score", 0)
            if complexity_score > 0.7:
                recommendations.append("복잡한 질문입니다. 여러 부분으로 나누어 질문하면 더 정확한 답변을 받을 수 있습니다.")
            
            # 전문성 기반 추천
            complexity_factors = query_analysis.get("complexity_factors", {})
            if complexity_factors.get("requires_legal_expertise"):
                recommendations.append("법률 관련 질문입니다. 정확한 법적 조언이 필요하다면 전문가와 상담하세요.")
            
            if complexity_factors.get("requires_technical_expertise"):
                recommendations.append("기술적 질문입니다. 구체적인 구현이 필요하다면 해당 분야 전문가에게 문의하세요.")
            
        except Exception as e:
            recommendations.append("추천 사항 생성 중 오류가 발생했습니다.")
        
        return recommendations[:5]  # 최대 5개 추천사항
    
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
    
    def _save_system_interaction(self, 
                               query: str, 
                               response: Dict[str, Any], 
                               execution_time: float):
        """시스템 레벨 상호작용 저장"""
        try:
            self.system_memory.save_interaction(
                user_query=query,
                agent_response=response.get("final_answer", ""),
                tools_used=["multi_agent_system"],
                success=len(response.get("source_agents", [])) > 0
            )
            
            # 시스템 성능 패턴 학습
            pattern_data = {
                "execution_time": execution_time,
                "agent_count": len(response.get("source_agents", [])),
                "complexity_score": response.get("system_metadata", {}).get("query_analysis", {}).get("complexity_score", 0)
            }
            
            self.system_memory.learn_pattern(
                pattern_type="system_performance",
                pattern_data=pattern_data,
                success=len(response.get("source_agents", [])) > 0
            )
            
        except Exception as e:
            print(f"시스템 상호작용 저장 오류: {e}")
    
    def _create_error_response(self, error_message: str, additional_data: Dict = None) -> Dict[str, Any]:
        """오류 응답 생성"""
        error_response = {
            "query": "",
            "final_answer": error_message,
            "source_agents": [],
            "reasoning_process": f"시스템 오류: {error_message}",
            "execution_time": 0,
            "quality_metrics": {"error": True},
            "sources": [],
            "system_metadata": {
                "error": True,
                "error_message": error_message,
                "processing_timestamp": time.time()
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
            "manager_status": self.manager_agent.get_system_status(),
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
        print("[MultiAgentSystem] 시스템 리셋 완료")
    
    async def batch_process_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """배치 쿼리 처리"""
        print(f"[MultiAgentSystem] 배치 처리 시작: {len(queries)}개 쿼리")
        
        tasks = []
        for query in queries:
            task = asyncio.create_task(self.process_user_query(query))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        print(f"[MultiAgentSystem] 배치 처리 완료")
        return results 