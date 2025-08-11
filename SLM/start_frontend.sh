#!/bin/bash

echo "🎨 프론트엔드 시작 중..."

# 프론트엔드 디렉토리로 이동
cd frontend

# 필요한 패키지 설치 확인
echo "📦 npm 패키지 설치 확인 중..."
npm install

# 개발 서버 시작
echo "🌐 개발 서버 시작 중... (http://localhost:5173)"
echo "💡 백엔드 API 서버는 http://localhost:8000 에서 실행되어야 합니다"
echo "💡 백엔드가 실행되지 않은 경우 start_api_server.sh를 먼저 실행하세요"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo ""

npm run dev 