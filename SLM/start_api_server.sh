#!/bin/bash

echo "🚀 멀티 에이전트 시스템 API 서버 시작 중..."

# Python 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화 중..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 가상환경 활성화 중..."
    source .venv/bin/activate
fi

# 필요한 패키지 설치 확인
echo "📋 필요한 패키지 설치 확인 중..."
pip install -r requirements.txt

# API 서버 실행
echo "🌐 API 서버 실행 중... (http://localhost:8000)"
echo "💡 프론트엔드는 http://localhost:5173 에서 실행하세요"
echo "💡 API 문서는 http://localhost:8000/docs 에서 확인할 수 있습니다"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo ""

python3 api_server.py 