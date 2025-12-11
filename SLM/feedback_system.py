import time
import json
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import traceback

class ErrorType(Enum):
    TOOL_EXECUTION = "tool_execution"
    LLM_RESPONSE = "llm_response"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    UNKNOWN = "unknown"

class FeedbackSystem:
    """피드백 및 자기 수정 메커니즘"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_patterns = {}
        self.success_patterns = {}
        self.retry_strategies = {}
        
        # 기본 재시도 전략 설정
        self._setup_default_strategies()
    
    def _setup_default_strategies(self):
        """기본 재시도 전략 설정"""
        self.retry_strategies = {
            ErrorType.TOOL_EXECUTION: [
                self._retry_with_different_params,
                self._retry_with_fallback_tool,
                self._retry_with_simplified_query
            ],
            ErrorType.LLM_RESPONSE: [
                self._retry_with_different_prompt,
                self._retry_with_lower_temperature,
                self._retry_with_fallback_model
            ],
            ErrorType.CONNECTION: [
                self._retry_with_backoff,
                self._retry_with_alternative_endpoint
            ],
            ErrorType.TIMEOUT: [
                self._retry_with_shorter_timeout,
                self._retry_with_simplified_request
            ],
            ErrorType.VALIDATION: [
                self._retry_with_validation_fix,
                self._retry_with_alternative_format
            ]
        }
    
    def execute_with_feedback(self, 
                            func: Callable, 
                            *args, 
                            error_context: str = "",
                            **kwargs) -> Dict[str, Any]:
        """
        함수를 실행하고 실패 시 피드백을 통해 자동 수정 시도
        """
        attempt = 0
        last_error = None
        execution_log = []
        
        while attempt < self.max_retries:
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 성공 패턴 학습
                self._learn_success_pattern(func.__name__, args, kwargs, execution_time)
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "execution_time": execution_time,
                    "log": execution_log
                }
                
            except Exception as e:
                attempt += 1
                error_type = self._classify_error(e)
                error_info = {
                    "attempt": attempt,
                    "error_type": error_type.value,
                    "error_message": str(e),
                    "timestamp": time.time(),
                    "context": error_context,
                    "traceback": traceback.format_exc()
                }
                execution_log.append(error_info)
                last_error = e
                
                # 오류 패턴 학습
                self._learn_error_pattern(func.__name__, args, kwargs, error_type, str(e))
                
                # 마지막 시도가 아니라면 수정 시도
                if attempt < self.max_retries:
                    correction = self._get_correction_strategy(error_type, error_info, attempt)
                    if correction:
                        args, kwargs = correction.get("args", args), correction.get("kwargs", kwargs)
                        func = correction.get("func", func)
                        
                        # 재시도 전 대기
                        if self.retry_delay > 0:
                            time.sleep(self.retry_delay * attempt)
        
        # 모든 시도 실패
        return {
            "success": False,
            "error": str(last_error),
            "attempts": attempt,
            "log": execution_log
        }
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """오류 유형 분류"""
        error_str = str(error).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT
        elif "connection" in error_str or "network" in error_str:
            return ErrorType.CONNECTION
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorType.VALIDATION
        elif "tool" in error_str or "execution" in error_str:
            return ErrorType.TOOL_EXECUTION
        elif "llm" in error_str or "model" in error_str:
            return ErrorType.LLM_RESPONSE
        else:
            return ErrorType.UNKNOWN
    
    def _get_correction_strategy(self, 
                               error_type: ErrorType, 
                               error_info: Dict[str, Any], 
                               attempt: int) -> Optional[Dict[str, Any]]:
        """오류 유형에 따른 수정 전략 반환"""
        strategies = self.retry_strategies.get(error_type, [])
        
        if attempt <= len(strategies):
            strategy_func = strategies[attempt - 1]
            return strategy_func(error_info)
        
        return None
    
    def _retry_with_different_params(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """다른 매개변수로 재시도"""
        return {
            "kwargs": {
                "max_tokens": 512,  # 토큰 수 줄이기
                "temperature": 0.3  # 온도 낮추기
            }
        }
    
    def _retry_with_fallback_tool(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """대체 도구로 재시도"""
        return {
            "kwargs": {
                "use_fallback": True,
                "alternative_method": True
            }
        }
    
    def _retry_with_simplified_query(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """단순화된 쿼리로 재시도"""
        return {
            "kwargs": {
                "simplify_query": True,
                "reduce_complexity": True
            }
        }
    
    def _retry_with_different_prompt(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """다른 프롬프트로 재시도"""
        return {
            "kwargs": {
                "use_alternative_prompt": True,
                "prompt_strategy": "simple"
            }
        }
    
    def _retry_with_lower_temperature(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """더 낮은 온도로 재시도"""
        return {
            "kwargs": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
    
    def _retry_with_fallback_model(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """대체 모델로 재시도"""
        return {
            "kwargs": {
                "use_fallback_model": True,
                "model": "fallback"
            }
        }
    
    def _retry_with_backoff(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """백오프 전략으로 재시도"""
        attempt = error_info.get("attempt", 1)
        return {
            "kwargs": {
                "retry_delay": self.retry_delay * (2 ** attempt),
                "exponential_backoff": True
            }
        }
    
    def _retry_with_alternative_endpoint(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """대체 엔드포인트로 재시도"""
        return {
            "kwargs": {
                "use_alternative_endpoint": True,
                "backup_url": True
            }
        }
    
    def _retry_with_shorter_timeout(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """더 짧은 타임아웃으로 재시도"""
        return {
            "kwargs": {
                "timeout": 10,  # 10초로 단축
                "quick_response": True
            }
        }
    
    def _retry_with_simplified_request(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """단순화된 요청으로 재시도"""
        return {
            "kwargs": {
                "simplified_request": True,
                "reduce_payload": True
            }
        }
    
    def _retry_with_validation_fix(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """검증 수정으로 재시도"""
        return {
            "kwargs": {
                "skip_validation": False,
                "strict_validation": True,
                "auto_fix": True
            }
        }
    
    def _retry_with_alternative_format(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """대체 형식으로 재시도"""
        return {
            "kwargs": {
                "output_format": "json",
                "alternative_parser": True
            }
        }
    
    def _learn_error_pattern(self, 
                           func_name: str, 
                           args: tuple, 
                           kwargs: dict, 
                           error_type: ErrorType, 
                           error_message: str):
        """오류 패턴 학습"""
        pattern_key = f"{func_name}_{error_type.value}"
        
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = []
        
        self.error_patterns[pattern_key].append({
            "args": str(args),
            "kwargs": str(kwargs),
            "error_message": error_message,
            "timestamp": time.time()
        })
        
        # 최근 100개만 유지
        if len(self.error_patterns[pattern_key]) > 100:
            self.error_patterns[pattern_key] = self.error_patterns[pattern_key][-100:]
    
    def _learn_success_pattern(self, 
                             func_name: str, 
                             args: tuple, 
                             kwargs: dict, 
                             execution_time: float):
        """성공 패턴 학습"""
        pattern_key = f"{func_name}_success"
        
        if pattern_key not in self.success_patterns:
            self.success_patterns[pattern_key] = []
        
        self.success_patterns[pattern_key].append({
            "args": str(args),
            "kwargs": str(kwargs),
            "execution_time": execution_time,
            "timestamp": time.time()
        })
        
        # 최근 100개만 유지
        if len(self.success_patterns[pattern_key]) > 100:
            self.success_patterns[pattern_key] = self.success_patterns[pattern_key][-100:]
    
    def get_error_analysis(self, func_name: str = None) -> Dict[str, Any]:
        """오류 분석 반환"""
        if func_name:
            relevant_patterns = {k: v for k, v in self.error_patterns.items() if k.startswith(func_name)}
        else:
            relevant_patterns = self.error_patterns
        
        analysis = {
            "total_error_types": len(relevant_patterns),
            "error_frequency": {},
            "common_errors": [],
            "recent_errors": []
        }
        
        # 오류 빈도 계산
        for pattern_key, errors in relevant_patterns.items():
            error_type = pattern_key.split('_')[-1]
            analysis["error_frequency"][error_type] = len(errors)
            
            # 최근 오류
            if errors:
                recent_error = sorted(errors, key=lambda x: x["timestamp"])[-1]
                analysis["recent_errors"].append({
                    "pattern": pattern_key,
                    "error": recent_error
                })
        
        return analysis
    
    def get_success_analysis(self, func_name: str = None) -> Dict[str, Any]:
        """성공 분석 반환"""
        if func_name:
            relevant_patterns = {k: v for k, v in self.success_patterns.items() if k.startswith(func_name)}
        else:
            relevant_patterns = self.success_patterns
        
        analysis = {
            "total_successes": sum(len(v) for v in relevant_patterns.values()),
            "average_execution_time": 0,
            "success_rate_trends": {}
        }
        
        # 평균 실행 시간 계산
        all_times = []
        for successes in relevant_patterns.values():
            all_times.extend([s["execution_time"] for s in successes])
        
        if all_times:
            analysis["average_execution_time"] = sum(all_times) / len(all_times)
        
        return analysis 