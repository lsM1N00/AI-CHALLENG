"""
웹 검색 모듈 - Google Custom Search API 사용
"""
import requests
import os

class WebSearch:
    """웹 검색을 위한 클래스"""
    
    def __init__(self):
        """웹 검색 초기화"""
        self.api_key = os.getenv("GOOGLE_API_KEY", "your_google_api_key_here")
        self.search_engine_id = os.getenv("SEARCH_ENGINE_ID", "your_search_engine_id_here")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # API 키 확인
        if self.api_key == "your_google_api_key_here":
            print("Google API 키가 설정되지 않았습니다.")
    
    def search(self, query: str, num_results: int = 3) -> list:
        """
        구글 검색 수행
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            검색 결과 리스트 [{"title": str, "link": str, "snippet": str}, ...]
        """
        # API 키가 없으면 빈 결과 반환
        if self.api_key == "your_google_api_key_here":
            print("🔍 웹 검색 건너뜀 (API 키 없음)")
            return self._create_dummy_results(query)
        
        try:
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
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
                    "snippet": item.get("snippet", "요약 없음")
                })
            
            print(f"🔍 웹 검색 완료: {len(results)}개 결과")
            return results
            
        except requests.exceptions.Timeout:
            print("웹 검색 시간 초과")
            return []
        except requests.exceptions.RequestException as e:
            print(f"웹 검색 오류: {e}")
            return []
        except Exception as e:
            print(f" 예상치 못한 오류: {e}")
            return []
    
    def _create_dummy_results(self, query: str) -> list:
        """API 키가 없을 때 더미 결과 생성"""
        return [
            {
                "title": f"'{query}' 관련 정보",
                "link": "https://example.com",
                "snippet": "웹 검색 API가 설정되지 않아 실제 검색 결과를 가져올 수 없습니다."
            }
        ]

if __name__ == '__main__':
    # 테스트 실행
    searcher = WebSearch()
    test_query = "멀티 에이전트 시스템"
    results = searcher.search(test_query)
    
    print(f"\n검색어: {test_query}")
    print(f"결과 수: {len(results)}")
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   링크: {result['link']}")
        print(f"   요약: {result['snippet'][:100]}...")