"""
Transformers 기반 로컬 모델을 사용하는 LLM 핸들러
"""
import config
import requests
import json
import os

# Transformers import
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("⚠️ transformers가 설치되지 않았습니다. pip install transformers torch로 설치하세요.")
    TRANSFORMERS_AVAILABLE = False

class LLMHandler:
    """허깅페이스 모델을 사용하는 LLM 핸들러 (토큰 없이도 사용 가능)"""
    
    def __init__(self, model_name: str = "LEESangM1N/Qwen3-4B-general-fintune", temperature: float = 0.5):
        """
        LLM 핸들러 초기화 (로컬 transformers 모델 전용)
        
        Args:
            model_name: 허깅페이스 모델명 또는 로컬 모델 경로
            temperature: 응답 창의성 조절 (0.0-1.0)
        """
        self.model_name = model_name
        self.temperature = temperature
        
        # 로컬 transformers 모델만 사용 (원격 API 사용하지 않음)
        self.use_token = False
        
        print(f"🚀 로컬 transformers 모델 사용: {self.model_name}")
        print("💡 원격 API 호출하지 않고 로컬에서 모델을 실행합니다.")
        
        print(f"로컬 모델 초기화 완료: {self.model_name}")
    
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

            # 항상 로컬 transformers 모델 사용 (토큰이 있어도 API 사용하지 않음)
            return self._call_local_or_public_model(input_text, max_tokens)
                
        except Exception as e:
            error_msg = f"허깅페이스 모델 응답 생성 실패: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _call_remote_api(self, input_text: str, max_tokens: int) -> str:
        """원격 API 호출 (사용하지 않음 - 항상 로컬 모델 사용)"""
        print("⚠️ 원격 API 호출 시도됨 - 로컬 모델로 대체")
        return self._call_local_or_public_model(input_text, max_tokens)
    
    def _call_local_or_public_model(self, input_text: str, max_tokens: int) -> str:
        """Transformers 기반 로컬 모델 실행"""
        try:
            if not TRANSFORMERS_AVAILABLE:
                return "Transformers가 설치되지 않았습니다. pip install transformers torch로 설치하세요."
            
            # 모델과 토크나이저 로드 (캐시된 경우 재사용)
            if not hasattr(self, 'tokenizer') or not hasattr(self, 'model'):
                print(f"🔄 모델 로딩 중: {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
                
                # GPU 사용 가능한 경우 GPU로 이동
                if torch.cuda.is_available():
                    self.model = self.model.to('cuda')
                    print("✅ GPU 사용 모드로 설정")
                else:
                    print("💻 CPU 사용 모드로 설정")
            
            # 입력 텍스트 토크나이징 (token_type_ids 제거하여 경고 방지)
            inputs = self.tokenizer(input_text, return_tensors="pt", return_token_type_ids=False)
            
            # GPU 사용 시 입력을 GPU로 이동
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
            # 모델 추론
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=min(max_tokens, 4096),
                    temperature=self.temperature,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # 결과 디코딩
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 입력 텍스트 제거하고 새로 생성된 부분만 반환
            if input_text in generated_text:
                response_text = generated_text[len(input_text):].strip()
            else:
                response_text = generated_text.strip()
            
            print(f"✅ 로컬 모델 추론 완료: {len(response_text)}자 생성")
            return response_text
                
        except Exception as e:
            print(f"Error: {e}")
            return f"로컬 모델 추론 중 오류 발생: {str(e)}"
    
    def _extract_response_text(self, result) -> str:
        """응답에서 텍스트 추출 (로컬 모델 사용으로 인해 거의 사용되지 않음)"""
        # 로컬 모델에서는 이미 텍스트가 추출되어 반환됨
        return str(result)
    
    def set_temperature(self, temperature: float):
        """응답 창의성 조절"""
        self.temperature = max(0.0, min(1.0, temperature))
    
    def set_model(self, model_name: str):
        """모델 변경"""
        self.model_name = model_name
        print(f"모델이 {model_name}로 변경되었습니다.")
    
    def toggle_token_usage(self, use_token: bool):
        """토큰 사용 여부 토글 (항상 로컬 모델 사용)"""
        self.use_token = False  # 강제로 로컬 모델 사용
        print("🚀 로컬 transformers 모델 사용 모드 (토큰 사용 불가)")
        print("💡 API 호출하지 않고 로컬에서 모델을 실행합니다.")
    
    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "use_token": False,  # 항상 False
            "base_url": "로컬 transformers 모델",
            "execution_mode": "local"
        }

if __name__ == '__main__':
    # 테스트 실행
    llm = LLMHandler()
    test_prompt = "AI 멀티 에이전트 시스템이란 무엇인가요?"
    result = llm.get_response(test_prompt)
    print(f"질문: {test_prompt}")
    print(f"답변: {result}")
