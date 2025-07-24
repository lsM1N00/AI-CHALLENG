"""
LLM 핸들러 - Groq API를 사용한 언어 모델 처리
"""
from groq import Groq
import config

class LLMHandler:
    """Groq API를 사용한 LLM 핸들러"""
    
    def __init__(self, model_name: str = None, temperature: float = 0.5):
        """
        LLM 핸들러 초기화
        
        Args:
            model_name: 사용할 모델명 (기본값: config에서 가져옴)
            temperature: 응답 창의성 조절 (0.0-1.0)
        """
        self.model = model_name or config.LLM_MODEL_NAME
        self.temperature = temperature
        
        try:
            self.client = Groq(api_key=config.LLM_API_KEY)
            print(f"LLM 초기화 완료: {self.model}")
        except Exception as e:
            print(f"LLM 초기화 실패: {e}")
            self.client = None

    def get_response(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        프롬프트를 기반으로 LLM 응답 생성
        
        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            
        Returns:
            LLM 응답 텍스트
        """
        if not self.client:
            return "LLM 클라이언트가 초기화되지 않았습니다."

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=self.temperature,
                max_tokens=max_tokens,
                top_p=0.9,
                stream=False,
            )
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"LLM 응답 생성 실패: {str(e)}"
            print(f"{error_msg}")
            return error_msg

    def set_temperature(self, temperature: float):
        """응답 창의성 조절"""
        self.temperature = max(0.0, min(1.0, temperature))

if __name__ == '__main__':
    # 테스트 실행
    llm = LLMHandler()
    test_prompt = "AI 멀티 에이전트 시스템이란 무엇인가요?"
    result = llm.get_response(test_prompt)
    print(f"질문: {test_prompt}")
    print(f"답변: {result}")
