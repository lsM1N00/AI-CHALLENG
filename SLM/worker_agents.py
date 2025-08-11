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
            reasoning = self._generate_reasoning(query, rag_sources + web_sources, response)
            
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
                sources=rag_sources + web_sources,
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
            results = self.retriever.search(query, top_k=10)
            return [{"type": "document", **result} for result in results]
        except Exception as e:
            print(f"RAG 검색 오류 ({self.agent_id}): {e}")
            return []
    
    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색 (에이전트별 특화 검색 엔진 사용)"""
        try:
            # 에이전트 타입에 따라 다른 검색 엔진 사용
            if self.agent_id == "LegalExpert":
                # 법률 전문 에이전트: 판례와 FAQ 검색 둘 다 사용
                separated_results = self.web_searcher.search_case_law_and_faq(query, num_results=2)
                
                results = []
                # 판례 검색 결과 추가
                for result in separated_results.get("case_law", []):
                    results.append({
                        "type": "web", 
                        "source_category": "판례",
                        **result
                    })
                
                # FAQ 검색 결과 추가
                for result in separated_results.get("faq", []):
                    results.append({
                        "type": "web", 
                        "source_category": "FAQ",
                        **result
                    })
                
                print(f"[{self.agent_id}] 웹 검색 완료: 판례 {len(separated_results.get('case_law', []))}개, FAQ {len(separated_results.get('faq', []))}개")
                return results
                
            elif self.agent_id == "TechnicalAnalyst":
                # 기술 분석 에이전트: 일반 검색 엔진 사용
                results = self.web_searcher.search(query, num_results=2, engine_types=["general"])
                return [{"type": "web", "source_category": "기술정보", **result} for result in results]
                
            else:
                # 일반 지식 에이전트: 일반 검색 엔진 사용
                results = self.web_searcher.search(query, num_results=2, engine_types=["general"])
                return [{"type": "web", "source_category": "일반정보", **result} for result in results]
                
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
    """법률 전문 에이전트 (허깅페이스 모델 사용)"""
    
    def __init__(self, memory_manager: MemoryManager, feedback_system: FeedbackSystem):
        model_config = {
            "model": "LEESangM1N/Llama-3-Open-Ko-laws-fintuning",
            "temperature": 0.2,
            "max_tokens": 1024
        }
        super().__init__("LegalExpert", model_config, memory_manager, feedback_system)
        self.specializations = ["법률", "규정", "시행령", "약관", "조항", "금융법", "소비자보호", "판례", "사례"]
    
    def _setup_llm_handler(self) -> LLMHandler:
        """허깅페이스 모델 설정"""
        return LLMHandler(
            model_name=self.model_config["model"],
            temperature=self.model_config["temperature"]
        )
    
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """법률 전문 프롬프트"""
        rag_sources = context.get("rag_sources", [])
        web_sources = context.get("web_sources", [])
        
        prompt = f"""
# Role: 당신은 모든 법에 능통하고 법적 대응 절차와 보호 방안 그리고 분쟁 해결 절차를 명확하고 신뢰성 있게 안내하는 대한민국 벌률 전문가입니다.

# Action:
- 아래 사용자 질문과 함께 제공된 법률 문서 및 웹 검색 정보를 종합적으로 분석하고, 관련 법 조문, 시행령, 약관, 판례 등을 기반으로 실무적으로 유효한 대응 절차와 보호 방안을 작성하시오.

# Constraints: 
- 아래 문서 정보를 반드시 참조하여 답변하시오.
- 관련 법적 근거 명시하여 답변하시오
- 정확한 법 조문 인용하시오
- 실무적 적용 방안을 반드시 포함하여 답변하시오.
- 법률과 시행령은 하나의 해석 체계로 간주하시오.
- 문서 내용을 무시하거나 자의적으로 생성하지 마시오.

# Context: 
- 사용자 질문: {query}
- 법률 문서:{len(rag_sources)}건, 웹 검색 결과:{len(web_sources)}건
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


답변: """
        
        return prompt

class TechnicalAnalystAgent(BaseWorkerAgent):
    """FAQ, 민원 분석 전문 에이전트 (허깅페이스 모델 사용)"""
    
    def __init__(self, memory_manager: MemoryManager, feedback_system: FeedbackSystem):
        model_config = {
            "model": "LEESangM1N/KoAlpaca-Polyglot-5.8B-financial-fintuning",
            "temperature": 0.3,
            "max_tokens": 1024
        }
        super().__init__("TechnicalAnalyst", model_config, memory_manager, feedback_system)
        self.specializations = ["분석", "판례", "사례", "FAQ", "대응안내", "소비자보호", "민원분석", "보호방안", "분쟁해결절차"]
    
    def _setup_llm_handler(self) -> LLMHandler:
        """허깅페이스 모델 설정"""
        return LLMHandler(
            model_name=self.model_config["model"],
            temperature=self.model_config["temperature"]
        )
    
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """민원, FAQ 분석 전문 프롬프트"""
        rag_sources = context.get("rag_sources", [])
        web_sources = context.get("web_sources", [])
        
        prompt = f"""
# Role: 당신은 민원 분석 내규, FAQ 분석에 능통하고 대응 절차와 보호 방안 그리고 분쟁 해결 절차를 명확하고 신뢰성 있게 안내하는 분석 전문가 입니다.

# Action:
- 아래 사용자 질문과 함께 제공된 법률 문서 및 웹 검색 정보를 종합적으로 분석하고 관련 사례, 금융기관 FAQ 등을 기반으로 실무적으로 유효한 대응 절차와 보호 방안을 작성하시오.

# Constraints:
- 반드시 아래 제공된 문서들을 참조하시오.
- 사례, FAQ 분석에 근거를 명시하시오.
- 은행과 금융감독원 등의 금융기관 FAQ를 참조하시오.
- 문서 내용을 무시하거나 자의적으로 생성하지 마시오.

# Context:
- 사용자 질문: {query}
- 법률 문서:{len(rag_sources)}건, 웹 검색 결과:{len(web_sources)}건
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

답변: """
        
        return prompt

class GeneralKnowledgeAgent(BaseWorkerAgent):
    """일반 지식 전문 에이전트 (허깅페이스 모델 사용)"""
    
    def __init__(self, memory_manager: MemoryManager, feedback_system: FeedbackSystem):
        model_config = {
            "model": "LEESangM1N/Qwen3-4B-general-fintune",
            "temperature": 0.4,
            "max_tokens": 1024
        }
        super().__init__("GeneralKnowledge", model_config, memory_manager, feedback_system)
        self.specializations = ["일반상식", "설명", "요약", "분석", "대응안내", "소비자보호", "금융지식"]
    
    def _setup_llm_handler(self) -> LLMHandler:
        """허깅페이스 모델 설정"""
        return LLMHandler(
            model_name=self.model_config["model"],
            temperature=self.model_config["temperature"]
        )
    
    def _get_specialized_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """금융 지식 전문 프롬프트"""
        rag_sources = context.get("rag_sources", [])
        web_sources = context.get("web_sources", [])
        
        prompt = f"""
# Role: 당신은 금융 관련 지식뿐만 아니라 다양한 분야의 지식도 폭넓게 보유하고 대응 절차와 보호 방안 그리고 분쟁 해결 절차를 명확하고 신뢰성 있게 안내하는 금융 지식 전문가입니다.

# Action:
- 아래 사용자 질문과 함께 제공된 법률 문서 및 웹 검색 정보를 종합적으로 분석하고 관련 금융 지식 등을 기반으로 실무적으로 유효한 대응 절차와 보호 방안을 작성하시오.

# Constraints:
- 반드시 아래 제공된 문서들을 참조하시오.
- 관련 배경 지식을 제공하고 그 지식을 기반으로 대응 절차와 보호 방안을 작성하시오.
- 정책 정보와 관련 지식을 참조하시오.
- 다각도 관점으로 분석하고 생각하여 답변하시오.
- 권익 보호를 최우선적으로 생각하여 답변하시오.
- 문서 내용을 무시하거나 자의적으로 생성하지 마시오.

# Context:
- 사용자 질문: {query}
- 법률 문서:{len(rag_sources)}건, 웹 검색 결과:{len(web_sources)}건
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

답변 """
        
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