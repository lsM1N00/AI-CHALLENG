"""
웹 검색 모듈 - Google Custom Search API 사용
"""
import requests
import os
from typing import List, Dict, Any, Tuple
import config
import re
from keybert import KeyBERT

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
        
        # KeyBERT 모델 초기화 (한국어 처리에 최적화)
        self._init_keybert()
        
        # 도메인 특화 키워드 사전
        self._init_domain_keywords()
        
        # API 키 확인
        if self.api_key == "your_google_api_key_here":
            print("Google API 키가 설정되지 않았습니다.")
    
    def _init_keybert(self):
        """KeyBERT 모델 초기화"""
        try:
            # 한국어와 다국어 처리에 좋은 multilingual 모델 사용
            print("🤖 KeyBERT 모델 로딩 중...")
            self.keybert_model = KeyBERT(model='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            print("✅ KeyBERT 모델 로딩 완료")
        except Exception as e:
            print(f"⚠️ KeyBERT 모델 로딩 실패: {e}")
            print("📝 기본 키워드 추출 방식을 사용합니다.")
            self.keybert_model = None
    
    def _init_domain_keywords(self):
        """금융/법률 도메인 특화 키워드 사전 초기화"""
        # 동의어 사전
        self.synonyms = {
            # 금융 관련
            "대출": ["융자", "차입", "신용공여", "여신"],
            "연체": ["지연", "미납", "체납", "연체이자"],
            "과대대출": ["과도한대출", "과다대출", "과도대출"],
            "금리": ["이자율", "수익률", "금리부담"],
            "상환": ["변제", "갚기", "지급"],
            "담보": ["보증", "저당", "질권"],
            
            # 법률 관련
            "소송": ["재판", "법정다툼", "민사소송"],
            "중재": ["조정", "화해", "분쟁조정"],
            "배상": ["손해배상", "피해보상", "위자료"],
            "권리": ["권한", "법적권리", "소비자권리"],
            "의무": ["책임", "법적의무", "준수사항"],
            
            # 절차 관련
            "신청": ["접수", "요청", "청구"],
            "처리": ["진행", "수속", "절차"],
            "해결": ["처리", "대응", "조치"],
            "방법": ["절차", "수단", "방안"]
        }
        
        # 금융기관 매핑
        self.institution_mapping = {
            "은행": ["금융기관", "대출기관", "여신기관"],
            "금감원": ["금융감독원", "FSS"],
            "금융위": ["금융위원회", "FSC"],
            "신협": ["신용협동조합", "새마을금고"],
            "캐피탈": ["할부금융", "시설대여"]
        }
        
        # 법률 약어 확장
        self.law_expansions = {
            "금소법": "금융소비자보호법",
            "신용정보법": "신용정보의이용및보호에관한법률",
            "대출규제": "가계대출규제",
            "DSR": "총부채원리금상환비율"
        }
        
        # 금융/법률 도메인 특화 키워드 (KeyBERT 추출에 가중치 적용용)
        self.domain_keywords = {
            "금융": ["대출", "융자", "금리", "이자", "상환", "연체", "담보", "보증", "신용", "DSR"],
            "법률": ["법률", "조항", "규정", "소송", "배상", "권리", "의무", "위반", "처벌", "구제"],
            "기관": ["은행", "금감원", "금융위", "법원", "검찰", "경찰"],
            "절차": ["신청", "접수", "처리", "해결", "방법", "절차", "단계", "과정"]
        }
    
    def _advanced_preprocess(self, query: str) -> Dict[str, Any]:
        """고급 검색어 전처리 - KeyBERT 기반 다중 쿼리 생성"""
        result = {
            "original_query": query,
            "main_query": "",
            "expanded_queries": [],
            "specific_queries": [],
            "broad_queries": [],
            "intent": "",
            "keybert_keywords": [],
            "domain_keywords": [],
            "all_queries_keywords": {}  # 각 쿼리별 KeyBERT 키워드
        }
        
        # 1. 의도 분석
        result["intent"] = self._analyze_intent(query)
        
        # 2. KeyBERT 기반 키워드 추출
        result["keybert_keywords"] = self._extract_keywords_with_keybert(query)
        
        # 3. 도메인 특화 키워드 필터링
        result["domain_keywords"] = self._filter_domain_keywords(result["keybert_keywords"])
        
        # 4. 메인 쿼리 생성 (기존 전처리 개선)
        result["main_query"] = self._create_main_query(query)
        
        # 5. 확장 쿼리 생성 (동의어, 유사어 포함)
        result["expanded_queries"] = self._create_expanded_queries(query, result["keybert_keywords"])
        
        # 6. 구체적 쿼리 생성 (정확한 검색용)
        result["specific_queries"] = self._create_specific_queries(query, result["intent"])
        
        # 7. 넓은 범위 쿼리 생성 (관련 정보 수집용)
        result["broad_queries"] = self._create_broad_queries(query, result["keybert_keywords"])
        
        # 8. 모든 생성된 쿼리에서 KeyBERT 키워드 추출
        all_queries = [result["main_query"]] + result["expanded_queries"] + result["specific_queries"] + result["broad_queries"]
        for i, generated_query in enumerate(all_queries):
            if generated_query.strip():
                keywords = self._extract_keywords_with_keybert(generated_query)
                result["all_queries_keywords"][f"query_{i}"] = {
                    "query": generated_query,
                    "keywords": keywords
                }
        
        return result
    
    def _extract_keywords_with_keybert(self, text: str, max_keywords: int = 10) -> List[str]:
        """KeyBERT를 사용한 고급 키워드 추출"""
        if not self.keybert_model or not text.strip():
            # KeyBERT 모델이 없으면 기본 방식 사용
            return self._extract_keywords_fallback(text)
        
        try:
            # KeyBERT로 키워드 추출 (한국어에 최적화된 설정)
            keyword_scores = self.keybert_model.extract_keywords(
                text, 
                keyphrase_ngram_range=(1, 2),  # 1-2개 단어 조합 (성능 최적화)
                stop_words=None,  # 한국어 불용어 수동 처리
                use_mmr=True,  # 최대 마진 관련성
                diversity=0.7,  # 다양성 높임
                top_n=max_keywords * 2  # 더 많이 추출한 후 필터링
            )
            
            # 키워드만 추출 (점수 제거)
            raw_keywords = [keyword for keyword, score in keyword_scores]
            
            # 한국어 불용어 수동 제거
            filtered_keywords = self._filter_korean_stopwords(raw_keywords)
            
            # 도메인 특화 키워드 가중치 적용
            prioritized_keywords = self._prioritize_domain_keywords(filtered_keywords)
            
            return prioritized_keywords[:max_keywords]
            
        except Exception as e:
            print(f"⚠️ KeyBERT 키워드 추출 실패: {e}")
            return self._extract_keywords_fallback(text)
    
    def _filter_korean_stopwords(self, keywords: List[str]) -> List[str]:
        """한국어 불용어 수동 필터링"""
        # 한국어 불용어 리스트
        korean_stopwords = {
            '어떻게', '해야', '하나요', '해요', '인데', '에서', '에게', '에는', 
            '이', '가', '을', '를', '은', '는', '의', '와', '과', '하고',
            '그', '그것', '이것', '저것', '여기', '거기', '저기',
            '때문에', '때문', '그래서', '그러나', '하지만', '그리고',
            '수', '것', '등', '및', '또는', '및', '혹은'
        }
        
        filtered = []
        for keyword in keywords:
            # 불용어가 아니고, 길이가 2 이상인 키워드만 유지
            if (keyword not in korean_stopwords and 
                len(keyword) >= 2 and 
                not keyword.isdigit()):  # 숫자만으로 된 키워드 제외
                filtered.append(keyword)
        
        return filtered
    
    def _prioritize_domain_keywords(self, keywords: List[str]) -> List[str]:
        """도메인 특화 키워드에 우선순위 부여"""
        domain_keywords = []
        general_keywords = []
        
        # 모든 도메인 키워드를 하나의 리스트로 통합
        all_domain_keywords = []
        for category_keywords in self.domain_keywords.values():
            all_domain_keywords.extend(category_keywords)
        
        for keyword in keywords:
            # 도메인 키워드에 포함되거나 유사한 키워드 찾기
            is_domain = False
            for domain_keyword in all_domain_keywords:
                if domain_keyword in keyword or keyword in domain_keyword:
                    is_domain = True
                    break
            
            if is_domain:
                domain_keywords.append(keyword)
            else:
                general_keywords.append(keyword)
        
        # 도메인 키워드를 앞에, 일반 키워드를 뒤에 배치
        return domain_keywords + general_keywords
    
    def _filter_domain_keywords(self, keywords: List[str]) -> List[str]:
        """추출된 키워드 중 도메인 관련 키워드만 필터링"""
        domain_filtered = []
        
        # 모든 도메인 키워드를 하나의 리스트로 통합
        all_domain_keywords = []
        for category_keywords in self.domain_keywords.values():
            all_domain_keywords.extend(category_keywords)
        
        for keyword in keywords:
            # 도메인 키워드와 매칭되는지 확인
            for domain_keyword in all_domain_keywords:
                if domain_keyword in keyword or keyword in domain_keyword:
                    domain_filtered.append(keyword)
                    break
        
        return domain_filtered
    
    def _extract_keywords_fallback(self, text: str) -> List[str]:
        """KeyBERT 실패시 사용할 기본 키워드 추출"""
        # 불용어 리스트
        stopwords = ['어떻게', '해야', '하나요', '해요', '인데', '에서', '에게', '에는', '이', '가', '을', '를', '은', '는', '의', '와', '과', '하고']
        
        # 기본 토큰화 (공백 기준)
        words = text.split()
        
        # 불용어 제거 및 길이 필터링
        keywords = []
        for word in words:
            # 불용어 및 짧은 단어 제거
            if word not in stopwords and len(word) >= 2:
                # 특수문자 제거
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word:
                    keywords.append(clean_word)
        
        return keywords[:10]  # 최대 10개
    
    def _analyze_intent(self, query: str) -> str:
        """사용자 질문 의도 분석"""
        query_lower = query.lower()
        
        # 의도별 패턴 매칭
        intent_patterns = {
            "procedure": ["어떻게", "방법", "절차", "신청", "처리", "해야"],
            "problem_solving": ["해결", "대응", "조치", "당했을때", "문제"],
            "information": ["뭐", "무엇", "어떤", "종류", "설명"],
            "legal_rights": ["권리", "보호", "소송", "배상", "구제"],
            "regulation": ["규정", "법률", "조항", "위반", "처벌"],
            "calculation": ["계산", "금액", "이자", "수수료", "비용"]
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent
        
        return "general"
    
    def _create_main_query(self, query: str) -> str:
        """메인 쿼리 생성 (기존 방식 개선)"""
        # 기존 전처리 로직 활용
        main_query = self._simple_preprocess(query)
        
        # 법률 약어 확장
        for abbr, full_name in self.law_expansions.items():
            if abbr in main_query:
                main_query = main_query.replace(abbr, full_name)
        
        return main_query
    
    def _create_expanded_queries(self, query: str, keybert_keywords: List[str]) -> List[str]:
        """KeyBERT 키워드와 동의어/유사어를 포함한 확장 쿼리 생성"""
        expanded_queries = []
        
        # KeyBERT로 추출된 각 키워드에 대해 동의어 확장
        for keyword in keybert_keywords[:5]:  # 상위 5개 키워드만 사용
            if keyword in self.synonyms:
                for synonym in self.synonyms[keyword]:
                    # 원래 키워드를 동의어로 교체한 쿼리 생성
                    expanded_query = query.replace(keyword, synonym)
                    if expanded_query != query:
                        expanded_queries.append(self._simple_preprocess(expanded_query))
        
        # 금융기관 매핑 적용
        for institution, alternatives in self.institution_mapping.items():
            if institution in query:
                for alt in alternatives:
                    expanded_query = query.replace(institution, alt)
                    expanded_queries.append(self._simple_preprocess(expanded_query))
        
        # KeyBERT 키워드 조합으로 새로운 쿼리 생성
        if len(keybert_keywords) >= 2:
            # 상위 KeyBERT 키워드들로 새로운 조합 쿼리 생성
            for i in range(min(3, len(keybert_keywords))):
                for j in range(i+1, min(3, len(keybert_keywords))):
                    combo_query = f"{keybert_keywords[i]} {keybert_keywords[j]}"
                    expanded_queries.append(combo_query)
        
        return list(set(expanded_queries))  # 중복 제거
    
    def _create_specific_queries(self, query: str, intent: str) -> List[str]:
        """의도별 구체적 쿼리 생성"""
        specific_queries = []
        base_query = self._simple_preprocess(query)
        
        # 의도별 특화 키워드 추가
        intent_keywords = {
            "procedure": ["절차", "방법", "단계", "신청서"],
            "problem_solving": ["해결방법", "대응방안", "조치사항"],
            "legal_rights": ["법적권리", "구제방법", "소비자보호"],
            "regulation": ["법률조항", "규정", "위반사례"],
            "calculation": ["계산방법", "산정기준", "요율"]
        }
        
        if intent in intent_keywords:
            for keyword in intent_keywords[intent]:
                specific_query = f"{base_query} {keyword}"
                specific_queries.append(specific_query)
        
        return specific_queries
    
    def _create_broad_queries(self, query: str, keybert_keywords: List[str]) -> List[str]:
        """KeyBERT 키워드를 활용한 넓은 범위 검색 쿼리 생성"""
        broad_queries = []
        
        # KeyBERT 키워드만으로 간단한 쿼리 생성
        if len(keybert_keywords) >= 2:
            # 상위 2-3개 KeyBERT 키워드 조합
            for i in range(min(3, len(keybert_keywords))):
                for j in range(i+1, min(3, len(keybert_keywords))):
                    broad_query = f"{keybert_keywords[i]} {keybert_keywords[j]}"
                    broad_queries.append(broad_query)
        
        # 단일 KeyBERT 키워드 + 도메인 특화 키워드 조합
        domain_terms = ["법률", "해결방법", "절차", "권리", "보호"]
        for keyword in keybert_keywords[:3]:
            for domain_term in domain_terms:
                if domain_term not in keyword:
                    combo_query = f"{keyword} {domain_term}"
                    broad_queries.append(combo_query)
        
        # 도메인별 일반 쿼리 (KeyBERT 키워드 기반)
        financial_keywords = [kw for kw in keybert_keywords if any(fin_kw in kw for fin_kw in ["대출", "융자", "금리", "이자", "연체"])]
        legal_keywords = [kw for kw in keybert_keywords if any(leg_kw in kw for leg_kw in ["법", "권리", "소송", "배상", "위반"])]
        
        if financial_keywords:
            broad_queries.extend([f"{kw} 금융소비자보호" for kw in financial_keywords[:2]])
        if legal_keywords:
            broad_queries.extend([f"{kw} 구제방법" for kw in legal_keywords[:2]])
        
        return broad_queries[:10]  # 최대 10개로 제한
    
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
        구글 검색 수행 (KeyBERT 기반 고급 전처리 적용)
        
        Args:
            query: 검색 쿼리
            num_results: 각 엔진당 반환할 결과 수
            engine_types: 사용할 검색 엔진 타입들 ["case_law", "faq", "general"]
            
        Returns:
            검색 결과 리스트 [{"title": str, "link": str, "snippet": str, "source_type": str, "keybert_info": dict}, ...]
        """
        # 기본값: 모든 엔진 사용
        if engine_types is None:
            engine_types = ["case_law", "faq", "general"]
        
        # KeyBERT 기반 고급 전처리 수행
        preprocessed = self._advanced_preprocess(query)
        
        print(f"🔍 원본 쿼리: '{query}'")
        print(f"🎯 의도 분석: {preprocessed['intent']}")
        print(f"🔑 KeyBERT 키워드: {', '.join(preprocessed['keybert_keywords'])}")
        print(f"🏢 도메인 키워드: {', '.join(preprocessed['domain_keywords'])}")
        
        # API 키가 없으면 빈 결과 반환
        if self.api_key == "your_google_api_key_here":
            print("🔍 웹 검색 건너뜀 (API 키 없음)")
            return self._create_dummy_results(preprocessed['main_query'], engine_types)
        
        all_results = []
        
        # 엔진별 최적화된 쿼리 사용
        for engine_type in engine_types:
            if engine_type not in self.search_engines:
                print(f"❌ 알 수 없는 검색 엔진 타입: {engine_type}")
                continue
                
            engine_id = self.search_engines[engine_type]
            if engine_id == f"your_{engine_type}_engine_id" or not engine_id:
                print(f"🔍 {engine_type} 검색 엔진 ID가 설정되지 않았습니다.")
                continue
            
            try:
                # 엔진별 최적화된 쿼리 선택 (KeyBERT 정보 포함)
                queries_to_search = self._select_queries_for_engine_with_keybert(preprocessed, engine_type)
                
                engine_results = []
                for search_query_info in queries_to_search:
                    search_query = search_query_info["query"]
                    query_keywords = search_query_info["keywords"]
                    
                    try:
                        results = self._search_single_engine(search_query, num_results//len(queries_to_search) + 1, engine_id, engine_type)
                        
                        # 각 결과에 KeyBERT 정보 추가
                        for result in results:
                            result["keybert_info"] = {
                                "query_keywords": query_keywords,
                                "original_keywords": preprocessed['keybert_keywords'],
                                "domain_keywords": preprocessed['domain_keywords']
                            }
                        
                        engine_results.extend(results)
                    except Exception as e:
                        print(f"⚠️ 쿼리 '{search_query}' 검색 실패: {e}")
                        continue
                
                # 중복 제거 및 품질 필터링 (KeyBERT 정보 활용)
                engine_results = self._deduplicate_and_filter_with_keybert(engine_results, num_results, preprocessed)
                all_results.extend(engine_results)
                
                print(f"🔍 {engine_type} 검색 완료: {len(engine_results)}개 결과 (쿼리 {len(queries_to_search)}개 사용)")
                
            except Exception as e:
                print(f"❌ {engine_type} 검색 오류: {e}")
                continue
        
        # 최종 결과 정렬 및 선택 (KeyBERT 기반 관련성 점수 포함)
        final_results = self._rank_and_select_results_with_keybert(all_results, num_results * len(engine_types), preprocessed)
        
        print(f"🔍 전체 KeyBERT 기반 웹 검색 완료: {len(final_results)}개 결과")
        return final_results
    
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
    
    def _select_queries_for_engine_with_keybert(self, preprocessed: Dict[str, Any], engine_type: str) -> List[Dict[str, Any]]:
        """엔진별 최적화된 쿼리 선택 (KeyBERT 정보 포함)"""
        query_info_list = []
        
        if engine_type == "case_law":
            # 판례 검색: 구체적이고 법률 용어 포함된 쿼리 선호
            query_info_list.append({
                "query": preprocessed["main_query"],
                "keywords": preprocessed["keybert_keywords"]
            })
            
            # 도메인 키워드가 있는 구체적 쿼리 우선 선택
            for specific_query in preprocessed["specific_queries"][:2]:
                keywords = self._extract_keywords_with_keybert(specific_query)
                query_info_list.append({
                    "query": specific_query,
                    "keywords": keywords
                })
                
        elif engine_type == "faq":
            # FAQ 검색: 실용적이고 해결 방법 중심 쿼리 선호
            query_info_list.append({
                "query": preprocessed["main_query"],
                "keywords": preprocessed["keybert_keywords"]
            })
            
            if preprocessed["intent"] in ["procedure", "problem_solving"]:
                for specific_query in preprocessed["specific_queries"][:2]:
                    keywords = self._extract_keywords_with_keybert(specific_query)
                    query_info_list.append({
                        "query": specific_query,
                        "keywords": keywords
                    })
            else:
                for broad_query in preprocessed["broad_queries"][:1]:
                    keywords = self._extract_keywords_with_keybert(broad_query)
                    query_info_list.append({
                        "query": broad_query,
                        "keywords": keywords
                    })
                
        else:  # general
            # 일반 검색: 확장된 쿼리로 다양한 정보 수집
            query_info_list.append({
                "query": preprocessed["main_query"],
                "keywords": preprocessed["keybert_keywords"]
            })
            
            for expanded_query in preprocessed["expanded_queries"][:2]:
                keywords = self._extract_keywords_with_keybert(expanded_query)
                query_info_list.append({
                    "query": expanded_query,
                    "keywords": keywords
                })
                
            if preprocessed["broad_queries"]:
                broad_query = preprocessed["broad_queries"][0]
                keywords = self._extract_keywords_with_keybert(broad_query)
                query_info_list.append({
                    "query": broad_query,
                    "keywords": keywords
                })
        
        # 빈 쿼리 제거
        valid_queries = [qi for qi in query_info_list if qi["query"].strip()]
        
        return valid_queries[:3]  # 최대 3개 쿼리
    
    def _deduplicate_and_filter_with_keybert(self, results: List[Dict[str, Any]], max_results: int, preprocessed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """KeyBERT 정보를 활용한 중복 제거 및 품질 필터링"""
        if not results:
            return []
        
        # URL 기준 중복 제거
        seen_urls = set()
        filtered_results = []
        
        for result in results:
            url = result.get("link", "")
            if url not in seen_urls:
                seen_urls.add(url)
                
                # 기본 품질 필터링
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                
                # 너무 짧거나 의미없는 결과 필터링
                if len(title) > 10 and len(snippet) > 20:
                    # KeyBERT 키워드와의 관련성 점수 계산
                    relevance_score = self._calculate_keybert_relevance(result, preprocessed)
                    result["keybert_relevance"] = relevance_score
                    
                    filtered_results.append(result)
        
        # KeyBERT 관련성 점수로 정렬
        filtered_results.sort(key=lambda x: x.get("keybert_relevance", 0), reverse=True)
        
        return filtered_results[:max_results]
    
    def _calculate_keybert_relevance(self, result: Dict[str, Any], preprocessed: Dict[str, Any]) -> float:
        """KeyBERT 키워드를 활용한 관련성 점수 계산"""
        score = 0.0
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        text = f"{title} {snippet}"
        
        # 원본 KeyBERT 키워드와의 매칭
        for keyword in preprocessed.get("keybert_keywords", []):
            if keyword.lower() in text:
                score += 2.0  # KeyBERT 키워드 높은 점수
        
        # 도메인 키워드와의 매칭
        for keyword in preprocessed.get("domain_keywords", []):
            if keyword.lower() in text:
                score += 3.0  # 도메인 키워드 더 높은 점수
        
        # 제목에 키워드가 있으면 추가 점수
        for keyword in preprocessed.get("keybert_keywords", []):
            if keyword.lower() in title:
                score += 1.0
        
        return score
    
    def _rank_and_select_results_with_keybert(self, results: List[Dict[str, Any]], max_results: int, preprocessed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """KeyBERT 정보를 활용한 검색 결과 순위 매기기 및 선택"""
        if not results:
            return []
        
        # 종합 관련성 점수 계산
        for result in results:
            total_score = 0
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            
            # 기존 관련성 점수
            keybert_relevance = result.get("keybert_relevance", 0)
            total_score += keybert_relevance
            
            # 제목에 핵심 키워드가 있으면 높은 점수
            if any(keyword in title for keyword in ["법률", "금융", "소비자", "보호"]):
                total_score += 10
            
            # 스니펫에 해결/방법 관련 키워드가 있으면 점수 추가
            if any(keyword in snippet for keyword in ["방법", "해결", "절차", "신청"]):
                total_score += 5
            
            # 출처별 가중치
            source_type = result.get("source_type", "")
            if source_type == "case_law":
                total_score += 8  # 판례는 높은 점수
            elif source_type == "faq":
                total_score += 6  # FAQ는 중간 점수
            
            # 의도별 가중치
            intent = preprocessed.get("intent", "")
            if intent == "legal_rights" and source_type == "case_law":
                total_score += 5
            elif intent == "procedure" and source_type == "faq":
                total_score += 5
            
            result["total_relevance_score"] = total_score
        
        # 총 점수순으로 정렬
        results.sort(key=lambda x: x.get("total_relevance_score", 0), reverse=True)
        
        return results[:max_results]

    def search_case_law_and_faq(self, query: str, num_results: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """판례와 FAQ 검색 결과를 분리해서 반환 (KeyBERT 기반 고급 전처리 적용)"""
        # KeyBERT 기반 고급 전처리 수행
        preprocessed = self._advanced_preprocess(query)
        
        print(f"🔍 KeyBERT 기반 고급 검색 - 원본: '{query}'")
        print(f"🎯 의도: {preprocessed['intent']}")
        print(f"🔑 KeyBERT 키워드: {', '.join(preprocessed['keybert_keywords'])}")
        print(f"🏢 도메인 키워드: {', '.join(preprocessed['domain_keywords'])}")
        
        # API 키가 없으면 빈 결과 반환
        if self.api_key == "your_google_api_key_here":
            print("🔍 웹 검색 건너뜀 (API 키 없음)")
            return {
                "case_law": self._create_dummy_results(preprocessed['main_query'], ["case_law"]),
                "faq": self._create_dummy_results(preprocessed['main_query'], ["faq"])
            }
        
        results = {"case_law": [], "faq": []}
        
        for engine_type in ["case_law", "faq"]:
            engine_id = self.search_engines[engine_type]
            if engine_id == f"your_{engine_type}_engine_id" or not engine_id:
                print(f"🔍 {engine_type} 검색 엔진 ID가 설정되지 않았습니다.")
                continue
            
            try:
                # 엔진별 최적화된 쿼리 선택 (KeyBERT 정보 포함)
                queries_to_search = self._select_queries_for_engine_with_keybert(preprocessed, engine_type)
                
                engine_results = []
                for search_query_info in queries_to_search:
                    search_query = search_query_info["query"]
                    query_keywords = search_query_info["keywords"]
                    
                    try:
                        query_results = self._search_single_engine(search_query, num_results//len(queries_to_search) + 1, engine_id, engine_type)
                        
                        # 각 결과에 KeyBERT 정보 추가
                        for result in query_results:
                            result["keybert_info"] = {
                                "query_keywords": query_keywords,
                                "original_keywords": preprocessed['keybert_keywords'],
                                "domain_keywords": preprocessed['domain_keywords']
                            }
                        
                        engine_results.extend(query_results)
                    except Exception as e:
                        print(f"⚠️ {engine_type} 쿼리 '{search_query}' 검색 실패: {e}")
                        continue
                
                # KeyBERT 정보를 활용한 중복 제거 및 품질 필터링
                engine_results = self._deduplicate_and_filter_with_keybert(engine_results, num_results, preprocessed)
                results[engine_type] = engine_results
                
                print(f"🔍 {engine_type} KeyBERT 기반 고급 검색 완료: {len(engine_results)}개 결과")
                
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
    test_query = "과대대출을 받았는데 어떻게 해야해"
    
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