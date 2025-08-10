"""
LangGraph 기반 멀티 에이전트 시스템의 상태 관리
"""
from typing import Dict, List, Any, Optional, Annotated
from dataclasses import dataclass, field
import time
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

@dataclass
class AgentState:
    """에이전트 상태 클래스"""
    
    # 기본 쿼리 정보
    query: str = ""
    original_query: str = ""
    
    # 메시지 히스토리 (LangGraph 표준)
    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    
    # 쿼리 분석 결과
    query_analysis: Dict[str, Any] = field(default_factory=dict)
    complexity_score: float = 0.0
    estimated_processing_time: float = 0.0
    
    # 워커 에이전트 응답들 (1차)
    legal_response: Dict[str, Any] = field(default_factory=dict)
    technical_response: Dict[str, Any] = field(default_factory=dict)
    general_response: Dict[str, Any] = field(default_factory=dict)
    
    # 워커 에이전트 간 상호 피드백
    cross_feedback: Dict[str, Any] = field(default_factory=dict)
    
    # 피드백 반영 후 보완된 응답들 (2차)
    refined_legal_response: Dict[str, Any] = field(default_factory=dict)
    refined_technical_response: Dict[str, Any] = field(default_factory=dict)
    refined_general_response: Dict[str, Any] = field(default_factory=dict)
    
    # Manager의 종합 분석 결과
    manager_synthesis: Dict[str, Any] = field(default_factory=dict)
    consolidated_responses: List[Dict[str, Any]] = field(default_factory=list)
    
    # 응답 품질 분석
    quality_analysis: Dict[str, Any] = field(default_factory=dict)
    consistency_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # 선별된 최고 품질 응답들
    best_responses: List[Dict[str, Any]] = field(default_factory=list)
    
    # 최종 결과
    final_answer: str = ""
    reasoning_process: str = ""
    consolidated_sources: List[Dict[str, Any]] = field(default_factory=list)
    
    # 메타데이터
    execution_start_time: float = field(default_factory=time.time)
    execution_time: float = 0.0
    success: bool = False
    error_message: str = ""
    
    # 시스템 메트릭
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # 워크플로우 진행 상태
    current_step: str = ""
    next_step: str = ""
    completed_steps: List[str] = field(default_factory=list)
    
    # 응답 품질 평가
    response_quality: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """상태를 딕셔너리로 변환"""
        return {
            "query": self.query,
            "final_answer": self.final_answer,
            "reasoning_process": self.reasoning_process,
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message,
            "quality_metrics": self.quality_metrics,
            "consolidated_sources": self.consolidated_sources,
            "system_metadata": self.system_metadata
        }
    
    def mark_error(self, error_message: str):
        """오류 상태로 마킹"""
        self.success = False
        self.error_message = error_message
        self.should_continue = False
        self.execution_time = time.time() - self.execution_start_time
    
    def mark_success(self):
        """성공 상태로 마킹"""
        self.success = True
        self.execution_time = time.time() - self.execution_start_time
        self.should_continue = False
    
    def increment_retry(self) -> bool:
        """재시도 카운터 증가, 최대 재시도 횟수 확인"""
        self.retry_count += 1
        return self.retry_count <= self.max_retries

@dataclass 
class NodeResult:
    """노드 실행 결과"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    next_step: Optional[str] = None
    should_continue: bool = True 