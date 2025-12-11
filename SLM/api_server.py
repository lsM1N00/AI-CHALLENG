#!/usr/bin/env python3
"""
FastAPI 기반 멀티 에이전트 시스템 API 서버
병렬 실행이 포함된 LangGraph 시스템과 연결
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# LangGraph 시스템 import
try:
    from langgraph_multi_agent_system import LangGraphMultiAgentSystem
    from langgraph_agent_state import AgentState
    from memory_manager import MemoryManager
    SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LangGraph 시스템 import 실패: {e}")
    print("💡 기본 API만 제공됩니다.")
    SYSTEM_AVAILABLE = False

# FastAPI 앱 생성
app = FastAPI(
    title="멀티 에이전트 시스템 API",
    description="병렬 실행이 포함된 LangGraph 기반 멀티 에이전트 시스템",
    version="2.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 타임아웃 설정 (10분)
@app.middleware("http")
async def timeout_middleware(request, call_next):
    import asyncio
    try:
        # 10분(600초) 타임아웃 설정
        response = await asyncio.wait_for(call_next(request), timeout=600.0)
        return response
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={
                "success": False,
                "message": "요청 처리 시간이 초과되었습니다 (10분)",
                "error": "timeout"
            }
        )

# Pydantic 모델들
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    response: str
    session_id: str
    execution_time: float
    parallel_execution_info: Optional[Dict[str, Any]] = None

class SystemStatusResponse(BaseModel):
    success: bool
    status: str
    system_info: Dict[str, Any]
    parallel_execution: Dict[str, Any]

# 전역 변수
conversation_history: Dict[str, List[Dict[str, Any]]] = {}

# 시스템 초기화
@app.on_event("startup")
async def startup_event():
    """시스템 시작 시 초기화"""
    global SYSTEM_AVAILABLE
    print("🚀 멀티 에이전트 시스템 API 서버 시작 중...")
    
    if SYSTEM_AVAILABLE:
        try:
            # 멀티 에이전트 시스템 초기화
            app.state.agent_system = LangGraphMultiAgentSystem()
            print("✅ 멀티 에이전트 시스템 초기화 완료")
            
            # 병렬 실행 상태 확인
            status = app.state.agent_system.get_system_status()
            parallel_info = status.get('parallel_execution', {})
            print(f"🔄 병렬 실행 상태: {parallel_info.get('current_status', 'unknown')}")
            print(f"📊 최대 에이전트: {parallel_info.get('max_agents', 0)}")
            
        except Exception as e:
            print(f"❌ 멀티 에이전트 시스템 초기화 실패: {e}")
            SYSTEM_AVAILABLE = False
    else:
        print("⚠️ LangGraph 시스템 없이 기본 API만 제공")
    
    print("✅ API 서버 초기화 완료")

# 기본 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "멀티 에이전트 시스템 API 서버",
        "version": "2.0.0",
        "parallel_execution": "enabled",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system_available": SYSTEM_AVAILABLE
    }

@app.get("/status")
async def get_status():
    """시스템 상태 확인"""
    if not SYSTEM_AVAILABLE or not hasattr(app.state, 'agent_system'):
        return {
            "success": False,
            "message": "LangGraph 시스템이 초기화되지 않았습니다.",
            "system_available": False
        }
    
    try:
        status = app.state.agent_system.get_system_status()
        return {
            "success": True,
            "message": "시스템 상태 조회 성공",
            "system_info": status,
            "parallel_execution": status.get('parallel_execution', {})
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"상태 조회 실패: {str(e)}",
            "system_available": True
        }

# 채팅 엔드포인트
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """채팅 메시지 처리 (10분 타임아웃)"""
    try:
        start_time = time.time()
        
        # 타임아웃 설정 (10분)
        import asyncio
        try:
            # AI 응답 생성 (10분 제한)
            if SYSTEM_AVAILABLE and app.state.agent_system:
                try:
                    # LangGraph 시스템을 통한 응답 생성 (타임아웃 적용)
                    response = await asyncio.wait_for(
                        process_with_agents(request), 
                        timeout=600.0
                    )
                except asyncio.TimeoutError:
                    response = "AI 모델 처리 시간이 초과되었습니다. 더 간단한 질문으로 다시 시도해주세요."
                except Exception as e:
                    print(f"에이전트 시스템 오류: {e}")
                    response = generate_fallback_response(request.message)
            else:
                # 기본 응답 생성
                response = generate_fallback_response(request.message)
        except asyncio.TimeoutError:
            response = "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        
        # 세션 ID 생성 (없는 경우)
        if not request.session_id:
            request.session_id = f"session_{int(time.time())}"
        
        # 사용자 메시지를 대화 히스토리에 저장
        if request.user_id not in conversation_history:
            conversation_history[request.user_id] = []
        
        conversation_history[request.user_id].append({
            "timestamp": time.time(),
            "message": request.message,
            "type": "user"
        })
        
        # AI 응답을 대화 히스토리에 저장
        if conversation_history[request.user_id]:
            conversation_history[request.user_id][-1]["ai_response"] = response
        
        # 실행 시간 계산
        execution_time = time.time() - start_time
        
        # 병렬 실행 정보 수집
        parallel_info = None
        if SYSTEM_AVAILABLE and app.state.agent_system:
            try:
                status = app.state.agent_system.get_system_status()
                parallel_info = status.get('parallel_execution', {})
            except:
                pass
        
        return ChatResponse(
            success=True,
            message="응답 생성 완료",
            response=response,
            session_id=request.session_id,
            execution_time=execution_time,
            parallel_execution_info=parallel_info
        )
        
    except Exception as e:
        print(f"채팅 처리 오류: {e}")
        return ChatResponse(
            success=False,
            message=f"오류 발생: {str(e)}",
            response="죄송합니다. 오류가 발생했습니다.",
            session_id=request.session_id if hasattr(request, 'session_id') else "error",
            execution_time=0,
            parallel_execution_info=None
        )

async def process_with_agents(request: ChatRequest) -> str:
    """LangGraph 에이전트 시스템을 통한 메시지 처리"""
    try:
        # LangGraphMultiAgentSystem의 process_user_query 메서드 사용
        result = await app.state.agent_system.process_user_query(
            user_query=request.message,
            user_id=request.user_id
        )
        
        # 결과에서 응답 추출
        if result and result.get('success', False):
            final_answer = result.get('final_answer', '')
            if final_answer:
                return final_answer
            else:
                return "에이전트 시스템에서 응답을 생성했습니다"
        else:
            error_msg = result.get('error_message', '알 수 없는 오류')
            return f"에이전트 시스템 오류: {error_msg}"
        
    except Exception as e:
        print(f"에이전트 시스템 처리 오류: {e}")
        return f"에이전트 시스템 오류: {str(e)}"

def generate_fallback_response(message: str) -> str:
    """기본 응답 생성 (에이전트 시스템 없을 때)"""
    return f"죄송합니다. 현재 에이전트 시스템을 사용할 수 없습니다. 입력하신 메시지: {message}"

# 대화 히스토리 관련 엔드포인트
@app.get("/conversation/{user_id}")
async def get_conversation_history(user_id: str):
    """사용자별 대화 히스토리 조회"""
    if user_id not in conversation_history:
        return {"success": True, "conversations": []}
    
    return {
        "success": True,
        "conversations": conversation_history[user_id]
    }

@app.post("/reset")
async def reset_conversation(user_id: str = "default"):
    """대화 히스토리 리셋"""
    if user_id in conversation_history:
        conversation_history[user_id] = []
    
    if SYSTEM_AVAILABLE and hasattr(app.state, 'agent_system'):
        try:
            app.state.agent_system.reset_system()
            return {"success": True, "message": "시스템 및 대화 히스토리 리셋 완료"}
        except Exception as e:
            return {"success": False, "message": f"시스템 리셋 실패: {str(e)}"}
    
    return {"success": True, "message": "대화 히스토리 리셋 완료"}

@app.get("/export/{user_id}")
async def export_conversation(user_id: str):
    """대화 히스토리 내보내기"""
    if user_id not in conversation_history:
        return {"success": False, "message": "대화 히스토리가 없습니다."}
    
    return {
        "success": True,
        "user_id": user_id,
        "conversations": conversation_history[user_id],
        "export_time": time.time()
    }

# 시스템 정보 엔드포인트
@app.get("/modes")
async def get_available_modes():
    """사용 가능한 모드 반환"""
    return {
        "success": True,
        "modes": [
            {
                "id": "general",
                "name": "일반 상담",
                "description": "일반적인 질문과 답변"
            },
            {
                "id": "legal",
                "name": "법률 상담",
                "description": "법률 관련 질문과 답변"
            },
            {
                "id": "technical",
                "name": "기술 상담",
                "description": "기술적 문제 해결"
            }
        ]
    }

if __name__ == "__main__":
    print("🚀 멀티 에이전트 시스템 API 서버 시작...")
    print("💡 병렬 실행이 포함된 LangGraph 시스템과 연결됩니다.")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=600,
        timeout_graceful_shutdown=600
    ) 