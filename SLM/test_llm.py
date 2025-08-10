"""
허깅페이스 모델 테스트 스크립트
"""
import os
from dotenv import load_dotenv
from llm_handler import LLMHandler

# .env 파일에서 환경 변수 로드
load_dotenv()

def test_huggingface_models():
    """허깅페이스 모델들 테스트"""
    print("🔍 허깅페이스 모델 테스트 시작\n")
    
    # API 키 확인
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key or api_key == "your_huggingface_api_key_here":
        print("❌ HUGGINGFACE_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 HUGGINGFACE_API_KEY를 설정해주세요.")
        return False
    
    print("✅ HUGGINGFACE_API_KEY 확인됨")
    
    # 테스트할 모델들
    test_models = [
        {
            "name": "Microsoft DialoGPT-large",
            "model_id": "microsoft/DialoGPT-large",
            "temperature": 0.2,
            "test_prompt": "금융소비자보호법에 대해 간단히 설명해주세요."
        },
        {
            "name": "Microsoft DialoGPT-medium", 
            "model_id": "microsoft/DialoGPT-medium",
            "temperature": 0.3,
            "test_prompt": "대환대출이란 무엇인가요?"
        },
        {
            "name": "KoAlpaca-Polyglot",
            "model_id": "beomi/KoAlpaca-Polyglot-12.8B",
            "temperature": 0.4,
            "test_prompt": "안녕하세요, 한국어로 답변해주세요."
        },
        {
            "name": "Llama-2-7b-chat",
            "model_id": "meta-llama/Llama-2-7b-chat-hf",
            "temperature": 0.3,
            "test_prompt": "Hello, how are you today?"
        }
    ]
    
    success_count = 0
    
    for model_info in test_models:
        print(f"\n=== {model_info['name']} 테스트 ===")
        try:
            handler = LLMHandler(
                model_name=model_info['model_id'],
                temperature=model_info['temperature']
            )
            
            response = handler.get_response(model_info['test_prompt'])
            
            if response and not response.startswith("허깅페이스"):
                print(f"✅ 성공: {response[:100]}...")
                success_count += 1
            else:
                print(f"❌ 실패: {response}")
                
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
    
    print(f"\n📊 테스트 결과: {success_count}/{len(test_models)} 성공")
    return success_count > 0

def test_model_parameters():
    """모델 파라미터 테스트"""
    print("\n🔧 모델 파라미터 테스트")
    
    try:
        handler = LLMHandler(
            model_name="microsoft/DialoGPT-medium",
            temperature=0.1
        )
        
        # 온도 변경 테스트
        handler.set_temperature(0.8)
        print("✅ 온도 변경 성공")
        
        # 모델 변경 테스트
        handler.set_model("microsoft/DialoGPT-large")
        print("✅ 모델 변경 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 파라미터 테스트 실패: {str(e)}")
        return False

def test_error_handling():
    """오류 처리 테스트"""
    print("\n⚠️ 오류 처리 테스트")
    
    # 잘못된 모델명으로 테스트
    try:
        handler = LLMHandler(
            model_name="invalid/model/name",
            temperature=0.5
        )
        
        response = handler.get_response("테스트")
        print(f"응답: {response}")
        
    except Exception as e:
        print(f"예상된 오류 발생: {str(e)}")

if __name__ == "__main__":
    print("🚀 허깅페이스 모델 테스트 시작")
    print("=" * 50)
    
    # 기본 모델 테스트
    basic_success = test_huggingface_models()
    
    # 파라미터 테스트
    param_success = test_model_parameters()
    
    # 오류 처리 테스트
    test_error_handling()
    
    print("\n" + "=" * 50)
    if basic_success and param_success:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다.") 