"""
워커 에이전트 모듈 - 3개의 전문 에이전트 구현
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass

from llm_handler import LLMHandler
from document_retriever import DocumentRetriever
from web_search import WebSearch
from memory_manager import MemoryManager
from feedback_system import FeedbackSystem

@dataclass
class AgentResponse:
    """에이전트 응답 데이터 클래스"""
    agent_id: str
    response: str
    sources: List[Dict[str, Any]]
    reasoning: str
    execution_time: float
    success: bool
    error: Optional[str] = None

class BaseWorkerAgent(ABC):
    """워커 에이전트 기본 클래스"""
    
    def __init__(self, 
                 agent_id: str, 
                 model_config: Dict[str, Any],
                 memory_manager: MemoryManager,
                 feedback_system: FeedbackSystem):
        self.agent_id = agent_id
        self.model_config = model_config
        self.memory_manager = memory_manager
        self.feedback_system = feedback_system
        self.retriever = DocumentRetriever()
        self.web_searcher = WebSearch()
        
        # 각 에이전트별 LLM 핸들러 설정
        self.llm_handler = self._setup_llm_handler()
        
        # 에이전트별 전문 분야
        self.specializations = []
        
    @abstractmethod
    def _setup_llm_handler(self) -> LLMHandler:
        """에이전트별 LLM 핸들러 설정"""
        pass
    
    @abstractmethod
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """에이전트별 전문화된 프롬프트 생성"""
        pass
    

    
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """쿼리 처리 및 응답 생성"""
        start_time = time.time()
        
        try:
            # 1. 메모리에서 관련 컨텍스트 조회
            memory_context = self.memory_manager.get_recent_context(limit=3)
            
            # 2. 정보 검색 (RAG + 웹 검색)
            rag_sources = await self._search_documents(query)
            web_sources = await self._search_web(query)
            
            # 3. 전문화된 프롬프트 생성
            full_context = {
                "query": query,
                "rag_sources": rag_sources,
                "web_sources": web_sources,
                "memory_context": memory_context,
                "agent_context": context or {}
            }
            
            specialized_prompt = self._get_specialized_prompt(query, full_context)
            
            # 4. LLM 응답 생성 (피드백 시스템과 함께)
            llm_result = self.feedback_system.execute_with_feedback(
                self.llm_handler.get_response,
                specialized_prompt,
                error_context=f"Agent {self.agent_id} processing query"
            )
            
            if not llm_result["success"]:
                            return AgentResponse(
                agent_id=self.agent_id,
                response="",
                sources=[],
                reasoning=f"LLM 처리 실패: {llm_result.get('error', '알 수 없는 오류')}",
                execution_time=time.time() - start_time,
                success=False,
                error=llm_result.get("error")
            )
            
            response = llm_result["result"]
            
            # 5. 추론 과정 생성
            reasoning = self._generate_reasoning(query, all_sources, response)
            
            # 7. 메모리에 상호작용 저장
            self.memory_manager.save_interaction(
                user_query=query,
                agent_response=response,
                tools_used=["rag_search", "web_search", "llm_generation"],
                success=True
            )
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                agent_id=self.agent_id,
                response=response,
                sources=all_sources,
                reasoning=reasoning,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                agent_id=self.agent_id,
                response="",
                sources=[],
                reasoning=f"에이전트 처리 중 오류 발생: {str(e)}",
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    async def _search_documents(self, query: str) -> List[Dict[str, Any]]:
        """문서 검색 (RAG)"""
        try:
            results = self.retriever.search(query, top_k=3)
            return [{"type": "document", **result} for result in results]
        except Exception as e:
            print(f"RAG 검색 오류 ({self.agent_id}): {e}")
            return []
    
    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색"""
        try:
            results = self.web_searcher.search(query, num_results=2)
            return [{"type": "web", **result} for result in results]
        except Exception as e:
            print(f"웹 검색 오류 ({self.agent_id}): {e}")
            return []
    
    def _generate_reasoning(self, query: str, sources: List[Dict], response: str) -> str:
        """추론 과정 생성"""
        reasoning_parts = []
        
        reasoning_parts.append(f"[{self.agent_id}] 쿼리 분석 완료")
        
        if sources:
            doc_sources = [s for s in sources if s.get("type") == "document"]
            web_sources = [s for s in sources if s.get("type") == "web"]
            
            if doc_sources:
                reasoning_parts.append(f"- RAG 검색에서 {len(doc_sources)}개 문서 발견")
            if web_sources:
                reasoning_parts.append(f"- 웹 검색에서 {len(web_sources)}개 소스 발견")
        
        reasoning_parts.append(f"- {self.agent_id}의 전문 분야를 활용하여 응답 생성")
        
        return " ".join(reasoning_parts)

class LegalExpertAgent(BaseWorkerAgent):
    """법률 전문 에이전트 (Groq Llama 사용)"""
    
    def __init__(self, memory_manager: MemoryManager, feedback_system: FeedbackSystem):
        model_config = {
            "provider": "groq",
            "model": "llama3-70b-8192",
            "temperature": 0.2,
            "max_tokens": 1024
        }
        super().__init__("LegalExpert", model_config, memory_manager, feedback_system)
        self.specializations = ["법률", "규정", "조항", "금융법", "소비자보호"]
    
    def _setup_llm_handler(self) -> LLMHandler:
        """Groq Llama 모델 설정"""
        return LLMHandler()  # 기존 Groq 설정 사용
    
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """법률 전문 프롬프트"""
        rag_sources = context.get("rag_sources", [])
        web_sources = context.get("web_sources", [])
        
        prompt = f"""당신은 대한민국 법률 전문가입니다. 특히 금융소비자보호법과 관련 법규에 능통합니다.

사용자 질문: {query}

제공된 정보:
"""
        
        if rag_sources:
            prompt += "\n[법률 문서 정보]\n"
            for idx, source in enumerate(rag_sources[:3], 1):
                prompt += f"{idx}. {source.get('content', '')[:200]}...\n"
        
        if web_sources:
            prompt += "\n[웹 검색 정보]\n"
            for idx, source in enumerate(web_sources[:2], 1):
                prompt += f"{idx}. {source.get('title', '')}: {source.get('snippet', '')}\n"
        
        prompt += """
법률 전문가로서 다음 원칙에 따라 답변하세요:
1. 정확한 법조문 인용
2. 판례나 해석례 참조
3. 법적 근거 명시
4. 실무적 적용 방안 제시
5. 관련 법률 간 관계 설명

답변:"""
        
        return prompt

class TechnicalAnalystAgent(BaseWorkerAgent):
    """기술 분석 전문 에이전트 (OpenAI GPT 사용)"""
    
    def __init__(self, memory_manager: MemoryManager, feedback_system: FeedbackSystem):
        model_config = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 1024
        }
        super().__init__("TechnicalAnalyst", model_config, memory_manager, feedback_system)
        self.specializations = ["기술", "시스템", "구현", "아키텍처", "개발"]
    
    def _setup_llm_handler(self) -> LLMHandler:
        """OpenAI GPT 모델 설정 (시뮬레이션)"""
        # 실제로는 OpenAI API를 사용하지만, 여기서는 기존 LLM 핸들러 사용
        return LLMHandler()
    
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """기술 분석 전문 프롬프트"""
        rag_sources = context.get("rag_sources", [])
        web_sources = context.get("web_sources", [])
        
        prompt = f"""당신은 시스템 아키텍처와 기술 구현에 전문성을 가진 기술 분석가입니다.

사용자 질문: {query}

제공된 정보:
"""
        
        if rag_sources:
            prompt += "\n[문서 정보]\n"
            for idx, source in enumerate(rag_sources[:3], 1):
                prompt += f"{idx}. {source.get('content', '')[:200]}...\n"
        
        if web_sources:
            prompt += "\n[웹 검색 정보]\n"
            for idx, source in enumerate(web_sources[:2], 1):
                prompt += f"{idx}. {source.get('title', '')}: {source.get('snippet', '')}\n"
        
        prompt += """
기술 전문가로서 다음 관점에서 답변하세요:
1. 기술적 구현 방법론
2. 시스템 아키텍처 고려사항
3. 성능 및 확장성 분석
4. 보안 및 안정성 평가
5. 실제 구현 예시 및 코드

답변:"""
        
        return prompt

class GeneralKnowledgeAgent(BaseWorkerAgent):
    """일반 지식 전문 에이전트 (Claude 사용)"""
    
    def __init__(self, memory_manager: MemoryManager, feedback_system: FeedbackSystem):
        model_config = {
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "temperature": 0.4,
            "max_tokens": 1024
        }
        super().__init__("GeneralKnowledge", model_config, memory_manager, feedback_system)
        self.specializations = ["일반상식", "교육", "설명", "요약", "분석"]
    
    def _setup_llm_handler(self) -> LLMHandler:
        """Claude 모델 설정 (시뮬레이션)"""
        # 실제로는 Anthropic API를 사용하지만, 여기서는 기존 LLM 핸들러 사용
        return LLMHandler()
    
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """일반 지식 전문 프롬프트"""
        rag_sources = context.get("rag_sources", [])
        web_sources = context.get("web_sources", [])
        
        prompt = f"""당신은 다양한 분야의 지식을 폭넓게 보유한 일반 지식 전문가입니다.

사용자 질문: {query}

제공된 정보:
"""
        
        if rag_sources:
            prompt += "\n[문서 정보]\n"
            for idx, source in enumerate(rag_sources[:3], 1):
                prompt += f"{idx}. {source.get('content', '')[:200]}...\n"
        
        if web_sources:
            prompt += "\n[웹 검색 정보]\n"
            for idx, source in enumerate(web_sources[:2], 1):
                prompt += f"{idx}. {source.get('title', '')}: {source.get('snippet', '')}\n"
        
        prompt += """
일반 지식 전문가로서 다음 방식으로 답변하세요:
1. 이해하기 쉬운 설명
2. 관련 배경 지식 제공
3. 다각도 관점 분석
4. 실생활 적용 예시
5. 추가 학습 방향 제시

답변:"""
        
        return prompt

class WorkerAgentPool:
    """워커 에이전트 풀 관리"""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.feedback_system = FeedbackSystem()
        
        # 3개의 워커 에이전트 초기화
        self.agents = {
            "legal": LegalExpertAgent(self.memory_manager, self.feedback_system),
            "technical": TechnicalAnalystAgent(self.memory_manager, self.feedback_system),
            "general": GeneralKnowledgeAgent(self.memory_manager, self.feedback_system)
        }
    
    async def process_query_all_agents(self, query: str) -> List[AgentResponse]:
        """모든 에이전트가 동시에 쿼리 처리"""
        tasks = []
        
        for agent_id, agent in self.agents.items():
            task = asyncio.create_task(agent.process_query(query))
            tasks.append(task)
        
        # 모든 에이전트의 응답을 기다림
        responses = await asyncio.gather(*tasks)
        
        return responses
    
    def get_agent_status(self) -> Dict[str, Any]:
        """에이전트 풀 상태 반환"""
        return {
            "total_agents": len(self.agents),
            "agents": {
                agent_id: {
                    "specializations": agent.specializations,
                    "model_config": agent.model_config
                }
                for agent_id, agent in self.agents.items()
            },
            "memory_status": self.memory_manager.get_session_context(),
            "feedback_status": self.feedback_system.get_error_analysis()
        } 