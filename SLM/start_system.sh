#!/bin/bash

echo "🚀 멀티 에이전트 시스템 전체 시작 중..."
echo "=================================="

# 스크립트 실행 권한 확인
chmod +x start_api_server.sh
chmod +x start_frontend.sh

# 백그라운드에서 API 서버 시작
echo "🌐 백엔드 API 서버 시작 중..."
./start_api_server.sh &
API_PID=$!

# API 서버가 시작될 때까지 대기 (AI 모델 초기화 시간 고려)
echo "⏳ API 서버 시작 대기 중... (AI 모델 초기화로 인해 시간이 오래 걸릴 수 있습니다)"
echo "🔄 서버 상태 확인 중..."

# 최대 5분(300초)까지 대기하며 서버 상태 확인
for i in {1..60}; do
    echo "   ${i}/60 시도 중... (${i}0초 경과 / 5분)"
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API 서버가 성공적으로 시작되었습니다!"
        break
    fi
    
    if [ $i -eq 60 ]; then
        echo "❌ API 서버 시작에 실패했습니다. (5분 초과)"
        echo "💡 백엔드 로그를 확인해주세요."
        echo "💡 AI 모델 초기화가 오래 걸리는 경우 더 기다려야 할 수 있습니다."
        kill $API_PID 2>/dev/null
        exit 1
    fi
    
    sleep 5
done

# 프론트엔드 시작
echo "🎨 프론트엔드 시작 중..."
./start_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "🎉 시스템이 성공적으로 시작되었습니다!"
echo "=================================="
echo "🌐 백엔드 API: http://localhost:8000"
echo "📚 API 문서: http://localhost:8000/docs"
echo "🎨 프론트엔드: http://localhost:5173"
echo ""
echo "💡 시스템을 종료하려면 이 터미널에서 Ctrl+C를 누르세요"
echo "💡 또는 각 서비스를 개별적으로 종료할 수 있습니다:"
echo "   - 백엔드: kill $API_PID"
echo "   - 프론트엔드: kill $FRONTEND_PID"
echo ""

# 종료 시그널 처리
trap 'echo ""; echo "🛑 시스템 종료 중..."; kill $API_PID $FRONTEND_PID 2>/dev/null; exit 0' INT TERM

# 두 프로세스가 모두 실행되는 동안 대기
wait 