"""
웹 검색 모듈 - Google Custom Search API 사용
"""
import requests
import os
from typing import List, Dict, Any
import config

class WebSearch:
    """웹 검색을 위한 클래스"""
    
    def __init__(self):
        """웹 검색 초기화"""
        self.api_key = config.GOOGLE_API_KEY
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # 여러 검색 엔진 ID들
        self.search_engines = {
            "case_law": config.CASE_LAW_SEARCH_ENGINE_ID,  # 판례 검색 엔진
            "faq": config.FAQ_SEARCH_ENGINE_ID,  # FAQ 검색 엔진
            "general": config.SEARCH_ENGINE_ID  # 일반 검색 엔진
        }
        
        # API 키 확인
        if self.api_key == "your_google_api_key_here":
            print("Google API 키가 설정되지 않았습니다.")
    
    def _simple_preprocess(self, query: str) -> str:
        """간단한 검색어 전처리"""
        # 1. 해결방법 키워드 추가 감지
        need_solution = False
        solution_patterns = ['어떻게 해', '해야해', '해야하나', '해결해야', '어떻게', '어떡해']
        for pattern in solution_patterns:
            if pattern in query:
                need_solution = True
                break
        
        # 2. 물음표 제거
        query = query.replace('?', '').replace('？', '')
        
        # 3. 긴 패턴부터 짧은 패턴 순으로 정리 (순서가 중요함)
        # 긴 패턴 먼저 처리
        query = query.replace('어떻게 해야하나요', '').replace('어떻게 해야해', '')
        query = query.replace('어떻게 해결해야', '').replace('해결해야 해요', '')
        query = query.replace('어떻게 해', '').replace('해결해야', '')
        
        # 중간 패턴들
        query = query.replace('해야하나요', '').replace('해야해', '')
        query = query.replace('해야하나', '').replace('해야', '')
        query = query.replace('하나요', '').replace('해요', '')
        
        # 단순 패턴들
        query = query.replace('어떻게', '').replace('어떡해', '')
        query = query.replace('당했는데', '').replace('생겼는데', '')
        query = query.replace('뭐예요', '').replace('뭐에요', '')
        
        # 특수 변환
        query = query.replace('넣어야해', '넣기 방법')
        query = query.replace('넣어야', '넣기')
        query = query.replace('신청해야해', '신청 방법')
        query = query.replace('신청해야', '신청 방법')
        
        # 4. 조사 정리 (의미를 해치지 않는 선에서)
        query = query.replace('를 ', ' ').replace('을 ', ' ')
        query = query.replace('이 ', ' ').replace('가 ', ' ')
        query = query.replace('은 ', ' ').replace('는 ', ' ')
        
        # 5. 불필요한 공백과 잔여 문자 정리
        query = ' '.join(query.split())  # 여러 공백을 하나로
        
        # 잔여 단일 문자 제거 (의미없는 조사나 어미 찌꺼기)
        words = query.split()
        cleaned_words = []
        for word in words:
            # 1-2글자 중에서 의미없는 것들 필터링
            if len(word) <= 2 and word in ['해', '야', '결', '요', '나', '는', '이', '가']:
                continue
            cleaned_words.append(word)
        
        query = ' '.join(cleaned_words)
        
        # 6. 해결방법 키워드 추가
        if need_solution and '해결방법' not in query and '방법' not in query:
            query = query + ' 해결방법'
        
        return query.strip()
    
    def search(self, query: str, num_results: int = 3, engine_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        구글 검색 수행 (여러 검색 엔진 지원)
        
        Args:
            query: 검색 쿼리
            num_results: 각 엔진당 반환할 결과 수
            engine_types: 사용할 검색 엔진 타입들 ["case_law", "faq", "general"]
            
        Returns:
            검색 결과 리스트 [{"title": str, "link": str, "snippet": str, "source_type": str}, ...]
        """
        # 기본값: 모든 엔진 사용
        if engine_types is None:
            engine_types = ["case_law", "faq", "general"]
        
        # 검색어 전처리
        original_query = query
        preprocessed_query = self._simple_preprocess(query)
        
        if preprocessed_query != original_query:
            print(f"🔍 검색어 전처리: '{original_query}' → '{preprocessed_query}'")
        
        # API 키가 없으면 빈 결과 반환
        if self.api_key == "your_google_api_key_here":
            print("🔍 웹 검색 건너뜀 (API 키 없음)")
            return self._create_dummy_results(preprocessed_query, engine_types)
        
        all_results = []
        
        for engine_type in engine_types:
            if engine_type not in self.search_engines:
                print(f"❌ 알 수 없는 검색 엔진 타입: {engine_type}")
                continue
                
            engine_id = self.search_engines[engine_type]
            if engine_id == f"your_{engine_type}_engine_id" or not engine_id:
                print(f"🔍 {engine_type} 검색 엔진 ID가 설정되지 않았습니다.")
                continue
            
            try:
                results = self._search_single_engine(preprocessed_query, num_results, engine_id, engine_type)
                all_results.extend(results)
                print(f"🔍 {engine_type} 검색 완료: {len(results)}개 결과")
                
            except Exception as e:
                print(f"❌ {engine_type} 검색 오류: {e}")
                continue
        
        print(f"🔍 전체 웹 검색 완료: {len(all_results)}개 결과")
        return all_results
    
    def _search_single_engine(self, query: str, num_results: int, engine_id: str, engine_type: str) -> List[Dict[str, Any]]:
        """단일 검색 엔진에서 검색 수행"""
        params = {
            'key': self.api_key,
            'cx': engine_id,
            'q': query,
            'num': min(num_results, 10),  # 최대 10개
            'hl': 'ko'  # 한국어 결과 우선
        }
        
        response = requests.get(self.base_url, params=params, timeout=10)
        response.raise_for_status()
        
        items = response.json().get("items", [])
        results = []
        
        for item in items:
            results.append({
                "title": item.get("title", "제목 없음"),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "요약 없음"),
                "source_type": engine_type  # 어떤 검색 엔진에서 나온 결과인지 표시
            })
        
        return results
    
    def search_case_law_and_faq(self, query: str, num_results: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """판례와 FAQ 검색 결과를 분리해서 반환"""
        # 검색어 전처리
        preprocessed_query = self._simple_preprocess(query)
        
        # API 키가 없으면 빈 결과 반환
        if self.api_key == "your_google_api_key_here":
            print("🔍 웹 검색 건너뜀 (API 키 없음)")
            return {
                "case_law": self._create_dummy_results(preprocessed_query, ["case_law"]),
                "faq": self._create_dummy_results(preprocessed_query, ["faq"])
            }
        
        results = {"case_law": [], "faq": []}
        
        for engine_type in ["case_law", "faq"]:
            engine_id = self.search_engines[engine_type]
            if engine_id == f"your_{engine_type}_engine_id" or not engine_id:
                print(f"🔍 {engine_type} 검색 엔진 ID가 설정되지 않았습니다.")
                continue
            
            try:
                engine_results = self._search_single_engine(preprocessed_query, num_results, engine_id, engine_type)
                results[engine_type] = engine_results
                print(f"🔍 {engine_type} 검색 완료: {len(engine_results)}개 결과")
                
            except Exception as e:
                print(f"❌ {engine_type} 검색 오류: {e}")
                results[engine_type] = []
        
        return results
    
    def _create_dummy_results(self, query: str, engine_types: List[str]) -> List[Dict[str, Any]]:
        """API 키가 없을 때 더미 결과 생성"""
        dummy_results = []
        for engine_type in engine_types:
            dummy_results.append({
                "title": f"'{query}' 관련 {engine_type} 정보",
                "link": "https://example.com",
                "snippet": f"{engine_type} 검색 API가 설정되지 않아 실제 검색 결과를 가져올 수 없습니다.",
                "source_type": engine_type
            })
        return dummy_results

if __name__ == '__main__':
    # 테스트 실행
    searcher = WebSearch()
    test_query = "대출사기"
    
    # 판례와 FAQ 검색 테스트
    separated_results = searcher.search_case_law_and_faq(test_query)
    
    print(f"\n검색어: {test_query}")
    print(f"판례 결과 수: {len(separated_results['case_law'])}")
    print(f"FAQ 결과 수: {len(separated_results['faq'])}")
    
    # 통합 검색 테스트
    all_results = searcher.search(test_query, engine_types=["case_law", "faq"])
    print(f"통합 결과 수: {len(all_results)}")
    
    for i, result in enumerate(all_results, 1):
        print(f"\n{i}. [{result['source_type']}] {result['title']}")
        print(f"   링크: {result['link']}")
        print(f"   요약: {result['snippet'][:100]}...")