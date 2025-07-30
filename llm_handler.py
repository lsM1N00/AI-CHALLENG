"""
다중 LLM 핸들러 - OpenAI, Anthropic, Google, Groq API 지원
"""
import config

class LLMHandler:
    """다중 LLM provider를 지원하는 핸들러"""
    
    def __init__(self, provider: str = "groq", model_name: str = None, temperature: float = 0.5):
        """
        LLM 핸들러 초기화
        
        Args:
            provider: LLM provider ("openai", "anthropic", "google", "groq")
            model_name: 사용할 모델명
            temperature: 응답 창의성 조절 (0.0-1.0)
        """
        self.provider = provider.lower()
        self.temperature = temperature
        self.client = None
        
        # provider별 모델명 설정
        if model_name:
            self.model = model_name
        else:
            self.model = self._get_default_model()
        
        # provider별 클라이언트 초기화
        try:
            self._initialize_client()
            print(f"LLM 초기화 완료: {self.provider} - {self.model}")
        except Exception as e:
            print(f"LLM 초기화 실패: {e}")
            self.client = None
    
    def _get_default_model(self) -> str:
        """provider별 기본 모델명 반환"""
        defaults = {
            "openai": "gpt-4.1",
            "anthropic": "claude-sonnet-4-20250514", 
            "google": "gemini-2.5-pro",

        }
        return defaults.get(self.provider, "gpt-4.1")  # 기본값: GPT-4.1
    
    def _initialize_client(self):
        """provider별 클라이언트 초기화"""
        if self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            except ImportError:
                raise Exception("OpenAI 라이브러리가 설치되지 않았습니다. 'pip install openai' 실행")
                
        elif self.provider == "anthropic":
            try:
                import anthropic
                # test_claude.py 방식 (단순한 초기화)
                self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            except ImportError:
                raise Exception("Anthropic 라이브러리가 설치되지 않았습니다. 'pip install anthropic' 실행")
                
        elif self.provider == "google":
            try:
                from google import genai
                import os
                
                # HttpOptions 없이 단순하게 API 키만 사용
                API_KEY = os.environ.get("GEMINI_API_KEY")
                self.client = genai.Client(api_key=API_KEY)
            except ImportError:
                raise Exception("Google AI 라이브러리가 설치되지 않았습니다. 'pip install google-genai' 실행")
                
        # elif self.provider == "groq":  # Groq 미사용
        #     try:
        #         from groq import Groq
        #         self.client = Groq(api_key=config.LLM_API_KEY)
        #     except ImportError:
        #         raise Exception("Groq 라이브러리가 설치되지 않았습니다. 'pip install groq' 실행")
        else:
            raise Exception(f"지원하지 않는 provider입니다: {self.provider}")

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
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    top_p=0.9,
                )
                return response.choices[0].message.content
                
            elif self.provider == "anthropic":
                # test_claude.py 방식과 정확히 동일하게 API 호출
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                # test_claude.py에서는 message.content를 직접 출력 (리스트일 수 있음)
                if hasattr(message.content, '__iter__') and len(message.content) > 0:
                    return str(message.content[0].text) if hasattr(message.content[0], 'text') else str(message.content[0])
                else:
                    return str(message.content)
                
            elif self.provider == "google":
                # test_anthropic.py 방식과 동일하게 API 호출
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                return response.text
                
            # elif self.provider == "groq":  # Groq 미사용
            #     response = self.client.chat.completions.create(
            #         messages=[{"role": "user", "content": prompt}],
            #         model=self.model,
            #         temperature=self.temperature,
            #         max_tokens=max_tokens,
            #         top_p=0.9,
            #         stream=False,
            #     )
            #     return response.choices[0].message.content
                
            else:
                return f"지원하지 않는 provider입니다: {self.provider}"
                
        except Exception as e:
            error_msg = f"LLM 응답 생성 실패 ({self.provider}): {str(e)}"
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
