# AI agent
## 금융 소비자 권익 보호를 위한 AI agent
## 법 전처리 테스트시 "채권의 공정한 추심에 관한 법률.pdf"를 사용할 것을 권장합니다.
## postgresql에서 financedb에 접속
```bash
# 리눅스 환경에서 financedb 실행
sudo -u postgres psql financedb
```
```bash
# financedb렁 pgvector 연동
CREATE EXTENSION IF NOT EXISTS vector;
```
```bash
# 데이터베이스 테이블 구성 확인
\d 테이블명
# 테이블 종류 확인
\dt
```
# 멀티 AI agnet 전체 흐름도
3개의 전문 에이전트와 1개의 관리자 에이전트로 구성된 고도화된 AI agent 시스템

## 🏗️ 시스템 아키텍처

```mermaid
graph TB
    User["👤 사용자"] --> Main["🚀 MultiAgentApp<br/>(multi_agent_main.py)"]
    Main --> System["🏗️ MultiAgentSystem<br/>(multi_agent_system.py)"]
    
    System --> Analysis["📊 쿼리 분석"]
    Analysis --> Health["🔍 시스템 상태 점검"]
    Health --> Manager["👨‍💼 ManagerAgent<br/>(manager_agent.py)"]
    
    Manager --> Pool["👥 WorkerAgentPool<br/>(worker_agents.py)"]
    
    Pool --> Legal["⚖️ LegalExpert<br/>법률 전문 에이전트"]
    Pool --> Tech["🔧 TechnicalAnalyst<br/>기술 분석 에이전트"]
    Pool --> General["🌍 GeneralKnowledge<br/>일반 지식 에이전트"]
    
    Legal --> RAG1["📚 RAG 검색<br/>(document_retriever.py)"]
    Legal --> Web1["🌐 웹 검색<br/>(web_search.py)"]
    Legal --> LLM1["🤖 LLM 처리<br/>(llm_handler.py)"]
    
    Tech --> RAG2["📚 RAG 검색"]
    Tech --> Web2["🌐 웹 검색"]
    Tech --> LLM2["🤖 LLM 처리"]
    
    General --> RAG3["📚 RAG 검색"]
    General --> Web3["🌐 웹 검색"]
    General --> LLM3["🤖 LLM 처리"]
    
    RAG1 --> DB["🗄️ PostgreSQL<br/>+ pgvector"]
    RAG2 --> DB
    RAG3 --> DB
    
    Web1 --> Google["🔍 Google API"]
    Web2 --> Google
    Web3 --> Google
    
    LLM1 --> Response1["💬 응답 1"]
    LLM2 --> Response2["💬 응답 2"]
    LLM3 --> Response3["💬 응답 3"]
    
    Response1 --> Manager
    Response2 --> Manager
    Response3 --> Manager
    
    Manager --> Integration["🔄 응답 통합 및 품질 평가"]
    Integration --> Memory["💾 MemoryManager<br/>(memory_manager.py)"]
    Integration --> Feedback["📈 FeedbackSystem<br/>(feedback_system.py)"]
    
    Integration --> Final["✨ 최종 응답"]
    Final --> User
    
    classDef userClass fill:#e1f5fe
    classDef mainClass fill:#f3e5f5
    classDef systemClass fill:#e8f5e8
    classDef agentClass fill:#fff3e0
    classDef toolClass fill:#fce4ec
    classDef dataClass fill:#f1f8e9
    
    class User userClass
    class Main,System mainClass
    class Manager,Pool,Legal,Tech,General systemClass
    class RAG1,RAG2,RAG3,Web1,Web2,Web3,LLM1,LLM2,LLM3 agentClass
    class Memory,Feedback,DB,Google toolClass
    class Analysis,Health,Integration,Final dataClass
```
