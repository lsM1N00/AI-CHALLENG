"""
허깅페이스 모델 기반 LLM 핸들러
"""
import config
import requests
import json

class LLMHandler:
    """허깅페이스 모델을 사용하는 LLM 핸들러"""
    
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium", temperature: float = 0.5):
        """
        LLM 핸들러 초기화
        
        Args:
            model_name: 허깅페이스 모델명
            temperature: 응답 창의성 조절 (0.0-1.0)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = config.HUGGINGFACE_API_KEY
        self.base_url = config.HUGGINGFACE_BASE_URL
        
        if not self.api_key:
            print("⚠️ HUGGINGFACE_API_KEY가 설정되지 않았습니다.")
        
        print(f"허깅페이스 모델 초기화 완료: {self.model_name}")
    
    def get_response(self, prompt: str = None, messages: list = None, max_tokens: int = 4096) -> str:
        """
        프롬프트를 기반으로 허깅페이스 모델 응답 생성
        
        Args:
            prompt: 입력 프롬프트 (단순 문자열)
            messages: 구조화된 메시지 리스트 [{"role": "user", "content": "..."}]
            max_tokens: 최대 토큰 수
            
        Returns:
            모델 응답 텍스트
        """
        if not self.api_key:
            return "허깅페이스 API 키가 설정되지 않았습니다."

        try:
            # 프롬프트 준비
            if messages:
                # 메시지 리스트를 프롬프트로 변환
                formatted_prompt = ""
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        formatted_prompt += f"사용자: {content}\n"
                    elif role == "assistant":
                        formatted_prompt += f"어시스턴트: {content}\n"
                    elif role == "system":
                        formatted_prompt += f"시스템: {content}\n"
                input_text = formatted_prompt
            else:
                input_text = prompt or ""

            # 허깅페이스 API 호출
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": input_text,
                "parameters": {
                    "temperature": self.temperature,
                    "max_new_tokens": min(max_tokens, 4096),
                    "do_sample": True,
                    "top_p": 0.9,
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                f"{self.base_url}/models/{self.model_name}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # 응답 형식에 따라 텍스트 추출
                if isinstance(result, list) and len(result) > 0:
                    if "generated_text" in result[0]:
                        return result[0]["generated_text"]
                    elif "text" in result[0]:
                        return result[0]["text"]
                    else:
                        return str(result[0])
                elif isinstance(result, dict):
                    if "generated_text" in result:
                        return result["generated_text"]
                    elif "text" in result:
                        return result["text"]
                    else:
                        return str(result)
                else:
                    return str(result)
            else:
                error_msg = f"허깅페이스 API 호출 실패: {response.status_code} - {response.text}"
                print(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"허깅페이스 모델 응답 생성 실패: {str(e)}"
            print(error_msg)
            return error_msg

    def set_temperature(self, temperature: float):
        """응답 창의성 조절"""
        self.temperature = max(0.0, min(1.0, temperature))
    
    def set_model(self, model_name: str):
        """모델 변경"""
        self.model_name = model_name
        print(f"모델이 {model_name}로 변경되었습니다.")

if __name__ == '__main__':
    # 테스트 실행
    llm = LLMHandler()
    test_prompt = "AI 멀티 에이전트 시스템이란 무엇인가요?"
    result = llm.get_response(test_prompt)
    print(f"질문: {test_prompt}")
    print(f"답변: {result}")
