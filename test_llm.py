"""
LLM Provider 개별 테스트 스크립트
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_openai():
    """OpenAI GPT-4.1 테스트"""
    print("=== OpenAI GPT-4.1 테스트 ===")
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "안녕하세요, 간단한 테스트입니다."}],
            model="gpt-4.1",
            temperature=0.3,
            max_tokens=100
        )
        print("✅ OpenAI 성공:", response.choices[0].message.content[:50] + "...")
        return True
    except Exception as e:
        print("❌ OpenAI 실패:", str(e))
        return False

def test_anthropic():
    """Anthropic Claude 4 Sonnet 테스트"""
    print("\n=== Anthropic Claude 4 Sonnet 테스트 ===")
    try:
        import anthropic
        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            default_headers={
                "anthropic-version": "2023-06-01"
            }
        )
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.3,
            messages=[{"role": "user", "content": "안녕하세요, 간단한 테스트입니다."}]
        )
        print("✅ Anthropic 성공:", response.content[0].text[:50] + "...")
        return True
    except Exception as e:
        print("❌ Anthropic 실패:", str(e))
        return False

def test_google():
    """Google Gemini 2.5 Pro 테스트"""
    print("\n=== Google Gemini 2.5 Pro 테스트 ===")
    try:
        # 먼저 google-genai 방식 시도
        try:
            from google import genai
            # HttpOptions 없이 단순하게 API 키만 사용
            API_KEY = os.getenv("GEMINI_API_KEY")
            client = genai.Client(api_key=API_KEY)
            
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents="안녕하세요."
            )
            print("✅ Google (google-genai) 성공:", response.text[:50] + "...")
            return True
        except ImportError:
            print("google-genai 패키지를 찾을 수 없음, google-generativeai 시도중...")
        except Exception as e:
            print(f"google-genai 방식 실패: {e}, google-generativeai 시도중...")
            
        # google-generativeai 방식 시도
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-pro")
        
        response = model.generate_content(
            "안녕하세요, 간단한 테스트입니다.",
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 100
            }
        )
        print("✅ Google (google-generativeai) 성공:", response.text[:50] + "...")
        return True
    except Exception as e:
        print("❌ Google 실패:", str(e))
        return False

def test_packages():
    """설치된 패키지 확인"""
    print("\n=== 패키지 설치 상태 확인 ===")
    packages = {
        "openai": "OpenAI",
        "anthropic": "Anthropic", 
        "google.genai": "Google GenAI (최신)",
        "google.generativeai": "Google GenerativeAI (구버전)"
    }
    
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"✅ {name}: 설치됨")
        except ImportError:
            print(f"❌ {name}: 미설치")

def main():
    print("🔍 LLM Provider 개별 테스트 시작\n")
    
    # 패키지 설치 상태 확인
    test_packages()
    
    # API 키 확인
    print("\n=== API 키 설정 확인 ===")
    api_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Anthropic",
        "GEMINI_API_KEY": "Gemini"
    }
    
    for key, name in api_keys.items():
        value = os.getenv(key)
        if value and value != f"your_{key.lower()}":
            print(f"✅ {name}: 설정됨")
        else:
            print(f"❌ {name}: 미설정")
    
    # 각 provider 테스트
    results = []
    results.append(test_openai())
    results.append(test_anthropic()) 
    results.append(test_google())
    
    # 결과 요약
    print(f"\n=== 테스트 결과 요약 ===")
    success_count = sum(results)
    print(f"성공: {success_count}/3")
    print(f"실패: {3-success_count}/3")
    
    if success_count == 3:
        print("🎉 모든 LLM provider가 정상 작동합니다!")
    else:
        print("⚠️ 일부 provider에서 문제가 발생했습니다.")

if __name__ == "__main__":
    main() 