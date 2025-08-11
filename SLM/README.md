# 🤖 LangGraph 기반 멀티 에이전트 시스템

## 📋 프로젝트 개요

이 프로젝트는 **LangGraph**를 기반으로 한 고도화된 멀티 에이전트 시스템입니다. 각 에이전트는 **Hugging Face 모델**을 사용하여 전문적인 역할을 수행하며, LangGraph의 체크포인터 기능을 통해 사용자와의 대화 내용을 자동으로 저장하고 관리합니다.

## ✨ 주요 기능

### 🔄 멀티 에이전트 협업
- **LegalExpertAgent**: 법률 관련 전문 지식 제공
- **TechnicalAnalystAgent**: 기술적 분석 및 해결책 제시  
- **GeneralKnowledgeAgent**: 일반적인 정보 및 상식 제공
- **ManagerAgent**: 모든 에이전트의 응답을 종합하여 최종 답변 생성

### 💾 대화 내용 자동 저장 (체크포인터)
- **LangGraph 체크포인터**: 모든 대화 내용을 자동으로 저장
- **사용자별 스레드 관리**: 각 사용자마다 독립적인 대화 스레드 유지
- **대화 히스토리 조회**: 이전 대화 내용을 언제든지 확인 가능
- **데이터 내보내기**: JSON/TXT 형식으로 대화 데이터 저장

### 🧠 지능형 워크플로우
- **쿼리 복잡도 분석**: 질문의 난이도에 따른 최적화된 처리
- **병렬 처리**: 여러 에이전트가 동시에 작업 수행
- **상호 피드백**: 에이전트 간 응답 검토 및 개선
- **품질 분석**: 최종 답변의 정확성 및 완성도 평가

## 🚀 설치 및 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd SLM
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정 (선택사항)
`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 허깅페이스 액세스 토큰 설정 (선택사항 - 토큰이 없어도 시스템 작동)
HUGGINGFACE_ACCESS_TOKEN=your_huggingface_access_token_here
HUGGINGFACE_BASE_URL=https://api-inference.huggingface.co

# API 키가 없어도 공개 모델을 사용할 수 있습니다
# 더 나은 성능을 원한다면 액세스 토큰을 설정하세요
```

**💡 중요:** 액세스 토큰이 없어도 시스템이 작동합니다!
- **액세스 토큰 있음**: 더 빠른 응답과 안정적인 서비스
- **액세스 토큰 없음**: 공개 모델을 사용하여 무료로 서비스 이용

## 🎯 사용 방법

### 대화형 모드 실행
```bash
python langgraph_main.py
```

### 주요 명령어
- `user <사용자ID>`: 사용자 변경
- `history`: 현재 사용자의 대화 히스토리 조회
- `clear_history`: 대화 히스토리 삭제
- `export json`: JSON 형식으로 대화 데이터 내보내기
- `export txt`: TXT 형식으로 대화 데이터 내보내기
- `threads`: 모든 대화 스레드 정보 확인
- `status`: 시스템 상태 확인
- `reset`: 시스템 리셋

### 프로그래밍 방식 사용
```python
from langgraph_multi_agent_system import LangGraphMultiAgentSystem

# 시스템 초기화
system = LangGraphMultiAgentSystem()

# 쿼리 처리 (대화 내용 자동 저장)
result = await system.process_user_query("질문 내용", user_id="사용자ID")

# 대화 히스토리 조회
history = system.get_conversation_history("사용자ID")

# 대화 데이터 내보내기
export_data = system.export_conversation_data("사용자ID", "json")
```

## 🏗️ 시스템 아키텍처

### LangGraph 워크플로우
```
사용자 입력 → 쿼리 분석 → 병렬 에이전트 실행 → 상호 피드백 → 
응답 보완 → Manager 종합 → 품질 분석 → 최종 답변 생성
```

### 체크포인터 구조
- **InMemorySaver**: 메모리 기반 대화 내용 저장
- **스레드 관리**: 사용자별 독립적인 대화 스레드
- **자동 저장**: 각 워크플로우 단계별 상태 자동 저장
- **데이터 복구**: 시스템 재시작 시에도 대화 내용 유지

## 🔧 허깅페이스 모델 설정

### 사용 중인 모델
- **LegalExpertAgent**: `microsoft/DialoGPT-large`
- **TechnicalAnalystAgent**: `microsoft/DialoGPT-medium`  
- **GeneralKnowledgeAgent**: `beomi/KoAlpaca-Polyglot-12.8B`
- **ManagerAgent**: `microsoft/DialoGPT-large`

### 모델 변경 방법
`worker_agents.py`와 `manager_agent.py`에서 `model_name`을 원하는 모델로 변경하세요.

### API 키 없이 사용하기
**💡 액세스 토큰이 없어도 시스템이 작동합니다!**

```python
# worker_agents.py에서 모델 설정
model_config = {
    "model": "microsoft/DialoGPT-medium",  # 원하는 모델명
    "temperature": 0.3,
    "max_tokens": 1024
}
```

**지원되는 공개 모델들:**
- **대화형**: `microsoft/DialoGPT-large`, `microsoft/DialoGPT-medium`
- **한국어**: `beomi/KoAlpaca-Polyglot-12.8B`, `kakaobrain/kogpt`
- **범용**: `gpt2`, `distilgpt2`

**주의사항:**
- 공개 모델은 첫 요청 시 로딩 시간이 필요할 수 있습니다
- 동시 사용자가 많으면 응답이 지연될 수 있습니다
- 더 안정적인 서비스를 원한다면 액세스 토큰을 설정하세요

## 📊 테스트

### 단위 테스트 실행
```bash
# LLM 핸들러 테스트
python test_llm.py

# 에이전트 테스트
python test_agents.py

# LangGraph 시스템 테스트
python test_langgraph_system.py
```

### 통합 테스트
```bash
# 전체 시스템 테스트
python test_langgraph_system.py
```

## 📈 성능 최적화

### 쿼리 복잡도 분석
- **단순 쿼리**: 기본 처리 시간 (5초)
- **복잡 쿼리**: 복잡도에 따른 추가 처리 시간
- **에이전트 라우팅**: 질문 유형에 따른 최적 에이전트 선택

### 병렬 처리
- **동시 실행**: 여러 에이전트가 병렬로 작업 수행
- **상호 피드백**: 에이전트 간 응답 검토 및 개선
- **효율적 리소스 활용**: 처리 시간 단축 및 품질 향상

## 🔍 문제 해결

### 일반적인 문제
1. **API 키 오류**: `.env` 파일의 API 키 확인
2. **모델 로딩 실패**: 인터넷 연결 및 API 상태 확인
3. **메모리 부족**: 대화 히스토리 정리 또는 시스템 리셋

### 로그 확인
시스템 실행 시 콘솔에 상세한 로그가 출력됩니다. 오류 발생 시 로그를 확인하여 문제를 파악하세요.

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.

---

**🚀 LangGraph와 Hugging Face 모델을 활용한 차세대 멀티 에이전트 시스템으로 지능적인 대화를 경험해보세요!** 