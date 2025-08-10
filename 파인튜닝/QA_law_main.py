
"""
법률 PDF 기반 QA 데이터셋 생성 시스템
Legal PDF QA Dataset Generation System
"""

import os
import sys
import json
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import hashlib
from collections import Counter

# 외부 라이브러리
import pandas as pd
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv

# Langchain 관련
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# 문서 처리
from unstructured.partition.pdf import partition_pdf

# 유사도 검사
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 환경 변수 로드
load_dotenv()

# 로깅 설정
def setup_logging(log_dir: str = "./logs") -> logging.Logger:
    """로깅 설정"""
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"legal_qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    # 로거 설정
    logger = logging.getLogger('LegalQA')
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


class LegalQAGenerator:
    """법률 PDF QA 생성기"""
    
    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.qa_pairs = []
        self.processed_files = []
        
        # LLM 초기화 (GPT-4o 우선, 실패 시 GPT-3.5-turbo로 전환)
        self.primary_model = config.get('model_name', 'gpt-4o')
        self.fallback_model = 'gpt-3.5-turbo'
        self.current_model = self.primary_model
        
        self.llm = ChatOpenAI(
            model=self.current_model,
            temperature=config.get('temperature', 0.1),
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )
        
        # 벡터라이저 초기화 (유사도 검사용)
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.existing_questions = []
        
    def extract_pdf_elements(self, filepath: str) -> List:
        """PDF에서 텍스트 요소 추출"""
        self.logger.info(f"PDF 파싱 중: {filepath}")
        
        try:
            elements = partition_pdf(
                filename=filepath,
                extract_images_in_pdf=False,
                infer_table_structure=True,  # 표 구조 추론
                chunking_strategy="by_title",
                max_characters=4000,
                new_after_n_chars=3800,
                combine_text_under_n_chars=2000,
                languages=["kor", "eng"],  # 한국어와 영어 지원
                size={"longest_edge": 2048},  # 이미지 크기 제한 (deprecated 경고 해결)
            )
            self.logger.info(f"추출된 요소 수: {len(elements)}")
            return elements
            
        except Exception as e:
            self.logger.error(f"PDF 파싱 오류: {e}")
            return []
    
    def detect_document_type(self, text: str) -> str:
        """문서 유형 감지"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ["법률", "법", "조항", "조", "항", "호", "목"]):
            return "law"  # 법률 문서
        elif any(keyword in text_lower for keyword in ["시행령", "시행규칙", "규정", "지침"]):
            return "regulation"  # 시행령/규정
        elif any(keyword in text_lower for keyword in ["판례", "판결", "재판", "법원"]):
            return "case_law"  # 판례
        else:
            return "general"  # 일반 법률 문서
    
    def detect_law_category(self, text: str) -> str:
        """법률 카테고리 감지"""
        categories = {
            "민법": ["민법", "계약", "채무", "물권", "상속", "친족"],
            "형법": ["형법", "범죄", "형벌", "죄", "처벌"],
            "상법": ["상법", "회사", "주식", "상업", "기업"],
            "행정법": ["행정법", "행정", "허가", "인가", "처분"],
            "민사소송법": ["민사소송법", "소송", "재판", "증거", "집행"],
            "형사소송법": ["형사소송법", "수사", "기소", "공소", "재판"],
            "노동법": ["노동법", "근로", "임금", "해고", "부당노동행위"],
            "금융법": ["금융법", "은행", "보험", "증권", "대출"],
            "지적재산권법": ["지적재산권", "특허", "상표", "저작권", "영업비밀"],
            "환경법": ["환경법", "오염", "보전", "자연", "생태"],
        }
        
        text_lower = text.lower()
        detected_categories = []
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_categories.append(category)
        
        # 가장 많이 매칭된 카테고리 반환
        if detected_categories:
            return Counter(detected_categories).most_common(1)[0][0]
        return "기타"
    
    def create_qa_prompt(self, doc_type: str = "law") -> PromptTemplate:
        """문서 유형에 따른 프롬프트 생성"""
        
        base_instruction = """당신은 법률 전문가입니다. 주어진 법률 관련 내용을 바탕으로 
일반인들이 실제로 궁금해할 만한 실용적인 질문과 답변을 생성해주세요.

중요: 질문과 답변에서 반드시 구체적인 법률 조항의 핵심 내용을 포함해야 합니다.
"유사한", "해당 법률", "이러한" 처럼 애매모호한 표현 대신 구체적인 법률 조항을 명시하세요.
단, 파일 제목을 그대로 사용하지 마세요. PDF 안의 내용에 있는 법률 조항을 사용하세요.
Context에서 언급된 실제 법률 내용을 그대로 사용하여 구체적으로 언급해야 합니다.

Context:
{context}

카테고리: {category}
"""
        
        if doc_type == "law":
            # 법률 문서용 프롬프트
            specific_instruction = """
이것은 법률 문서입니다. 다음 사항에 중점을 두어 {num_questions}개의 질문을 생성하세요:

1. Context에 나온 구체적인 법률 조항의 내용과 의미
2. 해당 법률의 적용 범위와 대상
3. 법률 위반 시의 효과와 결과
4. 일반인이 알아야 할 권리와 의무
5. 실제 사례에서의 적용 방법
6. 관련된 다른 법률과의 관계
7. 법률 해석의 주요 원칙
8. 실무에서 주의해야 할 사항

각 질문은 실제 일반인이 궁금해할 만한 구체적인 내용이어야 하며, 
Context에서 언급된 실제 법률 내용을 그대로 사용하여 구체적으로 언급해야 합니다.
답변에는 반드시 구체적인 법적 근거, 적용 방법, 주의사항을 포함해야 합니다.
"""
        elif doc_type == "case_law":
            # 판례용 프롬프트
            specific_instruction = """
이것은 판례입니다. 다음 사항에 중점을 두어 {num_questions}개의 질문을 생성하세요:

1. Context에 나온 구체적인 판례의 쟁점과 법원의 판단
2. 판례의 법적 의미와 중요성
3. 유사한 사건에 대한 참고 사항
4. 일반인이 알아야 할 법적 원칙
5. 판례가 실제 생활에 미치는 영향
6. 관련 법률 조항과의 관계
7. 향후 유사 사건의 예측
8. 실무에서의 적용 방안

각 질문은 실제 일반인이 궁금해할 만한 구체적인 내용이어야 하며, 
Context에서 언급된 실제 판례 내용을 그대로 사용하여 구체적으로 언급해야 합니다.
답변에는 반드시 구체적인 법적 원칙, 적용 방법, 주의사항을 포함해야 합니다.
"""
        else:
            # 일반 법률 문서용 프롬프트
            specific_instruction = """
이것은 법률 관련 문서입니다. 다음 사항에 중점을 두어 {num_questions}개의 질문을 생성하세요:

1. Context에 나온 구체적인 법률 내용과 의미
2. 해당 법률의 실무적 적용 방법
3. 일반인이 알아야 할 법적 권리와 의무
4. 법률 위반 시의 효과와 대응 방법
5. 관련된 법적 절차와 방법
6. 실무에서 주의해야 할 사항
7. 법률 해석의 주요 원칙
8. 실제 적용 시 고려사항

각 질문은 실무적이고 구체적이어야 하며, 
Context에서 언급된 실제 법률 내용을 그대로 사용하여 구체적으로 언급해야 합니다.
답변에는 반드시 구체적인 법적 근거, 적용 방법, 주의사항을 포함해야 합니다.
"""
        
        format_instruction = """
반드시 아래 JSON 형식으로 응답하세요:
```json
{{
    "category": "{category}",
    "question": "구체적이고 실용적인 질문 (법률 조항의 핵심 내용 포함)",
    "answer": "상세하고 실무적인 답변 (최소 100자 이상, 구체적인 법률 내용 포함)"
}},
{{
    "category": "{category}",
    "question": "또 다른 구체적인 질문",
    "answer": "또 다른 상세한 답변"
}}
중요:

모든 질문과 답변은 한국어로 작성
답변은 구체적이고 실용적이어야 함
Context에서 언급된 실제 법률 내용을 그대로 사용하여 구체적으로 언급해야 함
법적 근거가 있다면 포함
실제 행동 지침 포함
"해당 법률", "이러한 조항" 등의 모호한 표현 대신 Context의 실제 내용을 명시
답변에는 반드시 구체적인 법적 근거, 적용 방법, 주의사항을 포함해야 함 """
        
        full_prompt = base_instruction + specific_instruction + format_instruction
        
        return PromptTemplate(
            input_variables=["context", "category", "num_questions"],
            template=full_prompt
        )
    
    def parse_llm_response(self, response) -> List[Dict]:
        """LLM 응답 파싱"""
        try:
            content = response.content.strip()
            # JSON 블록 추출
            if "json" in content:
                content = content.split("json")[1].split("```")[0].strip()
            
            # 배열로 변환
            if not content.startswith("["):
                content = f"[{content}]"
            
            # 마지막 쉼표 제거
            content = content.replace(",]", "]").replace(",}", "}")
            
            return json.loads(content)
            
        except Exception as e:
            self.logger.error(f"JSON 파싱 오류: {e}")
            return []
    
    def check_similarity(self, new_question: str, threshold: float = 0.85) -> bool:
        """기존 질문과의 유사도 검사"""
        if not self.existing_questions:
            return False
        
        try:
            # 모든 질문을 벡터화
            all_questions = self.existing_questions + [new_question]
            vectors = self.vectorizer.fit_transform(all_questions)
            
            # 새 질문과 기존 질문들의 유사도 계산
            new_vector = vectors[-1]
            existing_vectors = vectors[:-1]
            
            similarities = cosine_similarity(new_vector, existing_vectors)[0]
            
            # 임계값 이상의 유사도가 있는지 확인
            max_similarity = max(similarities) if len(similarities) > 0 else 0
            
            if max_similarity > threshold:
                self.logger.debug(f"유사한 질문 발견 (유사도: {max_similarity:.2f})")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"유사도 검사 오류: {e}")
            return False
    
    def generate_qa_from_chunk(self, chunk_text: str, doc_type: str, category: str, num_questions: int = 2) -> List[Dict]:
        """청크에서 QA 생성"""
        prompt = self.create_qa_prompt(doc_type)
        
        # 최대 2번 시도 (primary 모델 실패 시 fallback 모델 사용)
        for attempt in range(2):
            try:
                chain = prompt | self.llm | self.parse_llm_response
                qa_list = chain.invoke({
                    "context": chunk_text,
                    "category": category,
                    "num_questions": str(num_questions)
                })
                
                # 유사도 검사 및 필터링
                filtered_qa = []
                for qa in qa_list:
                    if 'question' in qa and not self.check_similarity(qa['question']):
                        self.existing_questions.append(qa['question'])
                        filtered_qa.append(qa)
                
                return filtered_qa
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 토큰 한계 또는 API 오류인 경우 fallback 모델로 전환
                if (attempt == 0 and 
                    ('quota' in error_msg or 'limit' in error_msg or 'insufficient' in error_msg or 
                     'billing' in error_msg or 'payment' in error_msg or 'token' in error_msg)):
                    
                    self.logger.warning(f"Primary 모델({self.current_model}) 실패, fallback 모델({self.fallback_model})로 전환: {e}")
                    self.current_model = self.fallback_model
                    self.llm = ChatOpenAI(
                        model=self.current_model,
                        temperature=self.config.get('temperature', 0.1),
                        streaming=True,
                        callbacks=[StreamingStdOutCallbackHandler()],
                    )
                    continue
                else:
                    self.logger.error(f"QA 생성 오류 (시도 {attempt + 1}): {e}")
                    if attempt == 1:  # 마지막 시도도 실패한 경우
                        return []
        
        return []
    
    def process_pdf(self, filepath: str, num_questions_per_chunk: int = 2) -> int:
        """단일 PDF 처리"""
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"처리 시작: {os.path.basename(filepath)}")
        
        # PDF 요소 추출
        elements = self.extract_pdf_elements(filepath)
        if not elements:
            return 0
  
        # 문서 유형 감지
        full_text = " ".join([str(el) for el in elements[:10]])  # 처음 10개 요소로 판단
        doc_type = self.detect_document_type(full_text)
        self.logger.info(f"문서 유형: {doc_type}")
        
        # 각 청크 처리
        qa_count = 0
        valid_chunks = [el for el in elements if hasattr(el, 'text') and len(str(el.text)) > 200]
        
        with tqdm(total=len(valid_chunks), desc="청크 처리") as pbar:
            for idx, element in enumerate(valid_chunks):
                chunk_text = str(element.text)
                category = self.detect_law_category(chunk_text)
                
                # QA 생성
                qa_list = self.generate_qa_from_chunk(
                    chunk_text, 
                    doc_type, 
                    category, 
                    num_questions_per_chunk
                )
                
                # 메타데이터 추가
                for qa in qa_list:
                    qa['source_file'] = os.path.basename(filepath)
                    qa['doc_type'] = doc_type
                    qa['chunk_index'] = idx
                    qa['created_at'] = datetime.now().isoformat()
                    
                    self.qa_pairs.append(qa)
                    qa_count += 1
                
                pbar.update(1)
        
        self.processed_files.append(filepath)
        self.logger.info(f"생성된 QA 수: {qa_count}")
        
        return qa_count
    
    def process_multiple_pdfs(self, pdf_files: List[str]) -> None:
        """여러 PDF 파일 처리"""
        total_qa = 0
        checkpoint_interval = 10  # 10개 파일마다 체크포인트 저장
        
        for i, pdf_file in enumerate(pdf_files):
            if os.path.exists(pdf_file):
                count = self.process_pdf(pdf_file, self.config.get('questions_per_chunk', 2))
                total_qa += count
                
                # 체크포인트 저장 (10개 파일마다)
                if (i + 1) % checkpoint_interval == 0:
                    checkpoint_path = f"./output/qa_checkpoint_{i+1}.json"
                    self.save_dataset(checkpoint_path)
                    self.logger.info(f"체크포인트 저장: {checkpoint_path} (처리된 파일: {i+1}/{len(pdf_files)})")
            else:
                self.logger.warning(f"파일을 찾을 수 없음: {pdf_file}")
        
        self.logger.info(f"\n총 처리 파일: {len(self.processed_files)}")
        self.logger.info(f"총 생성 QA: {total_qa}")
    
    def save_dataset(self, output_path: str) -> None:
        """데이터셋 저장"""
        output_data = {
            "metadata": {
                "total_pairs": len(self.qa_pairs),
                "processed_files": len(self.processed_files),
                "generation_date": datetime.now().isoformat(),
                "config": self.config
            },
            "qa_pairs": self.qa_pairs
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"데이터셋 저장: {output_path}")


class LegalQAProcessor:
    """QA 데이터셋 후처리기"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.legal_terms = {
            "민법": ["민법"],
            "형법": ["형법"],
            "상법": ["상법"],
            "행정법": ["행정법"],
            "민사소송법": ["민사소송법"],
            "형사소송법": ["형사소송법"],
            "노동법": ["노동법"],
            "금융법": ["금융법"],
            "지적재산권법": ["지적재산권법"],
            "환경법": ["환경법"],
        }

    def validate_qa(self, qa: Dict) -> Tuple[bool, List[str]]:
        """QA 검증"""
        issues = []
        
        # 필수 필드 확인
        required_fields = ['category', 'question', 'answer']
        for field in required_fields:
            if field not in qa or not qa[field]:
                issues.append(f"필수 필드 누락: {field}")
        
        if issues:
            return False, issues
        
        # 형식 검증
        if not qa['question'].endswith('?'):
            qa['question'] += '?'
        
        # 길이 검증
        if len(qa['answer']) < 50:
            issues.append("답변이 너무 짧음")
        
        return len(issues) == 0, issues

    def enhance_answer(self, qa: Dict) -> Dict:
        """답변 품질 향상"""
        answer = qa['answer']
        
        # 법률 용어 정규화
        for standard, variations in self.legal_terms.items():
            for var in variations:
                answer = answer.replace(var, standard)
        
        # 법률명 강조
        for law in self.legal_terms.keys():
            if law in answer and f"「{law}」" not in answer:
                answer = answer.replace(law, f"「{law}」")
        
        qa['answer'] = answer
        return qa

    def remove_duplicates(self, qa_list: List[Dict]) -> List[Dict]:
        """중복 제거"""
        seen = set()
        unique_qa = []
        
        for qa in qa_list:
            # 질문 기반 해시
            qa_hash = hashlib.md5(qa['question'].encode()).hexdigest()
            
            if qa_hash not in seen:
                seen.add(qa_hash)
                unique_qa.append(qa)
        
        return unique_qa

    def process(self, input_path: str, output_path: str) -> Dict:
        """전체 후처리 프로세스"""
        self.logger.info("후처리 시작...")
        
        # 데이터 로드
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        qa_list = data.get('qa_pairs', [])
        metadata = data.get('metadata', {})
        
        self.logger.info(f"원본 QA 수: {len(qa_list)}")
        
        # 1. 검증
        valid_qa = []
        for qa in qa_list:
            is_valid, _ = self.validate_qa(qa)
            if is_valid:
                valid_qa.append(qa)
        
        self.logger.info(f"유효한 QA: {len(valid_qa)}")
        
        # 2. 품질 향상
        enhanced_qa = [self.enhance_answer(qa) for qa in valid_qa]
        
        # 3. 중복 제거
        unique_qa = self.remove_duplicates(enhanced_qa)
        self.logger.info(f"중복 제거 후: {len(unique_qa)}")
        
        # 통계 생성
        stats = self.generate_statistics(unique_qa)
        
        # 결과 저장
        output_data = {
            "metadata": {
                **metadata,
                "processed_date": datetime.now().isoformat(),
                "statistics": stats
            },
            "qa_pairs": unique_qa
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"후처리 완료: {output_path}")
        
        return stats

    def generate_statistics(self, qa_list: List[Dict]) -> Dict:
        """통계 생성"""
        if not qa_list:
            return {
                "total": 0,
                "by_category": {},
                "by_doc_type": {},
                "avg_answer_length": 0,
                "avg_question_length": 0
            }
        
        df = pd.DataFrame(qa_list)
        
        stats = {
            "total": len(qa_list),
            "by_category": df['category'].value_counts().to_dict() if 'category' in df.columns else {},
            "by_doc_type": df.get('doc_type', pd.Series()).value_counts().to_dict() if 'doc_type' in df.columns else {},
            "avg_answer_length": int(df['answer'].str.len().mean()) if 'answer' in df.columns else 0,
            "avg_question_length": int(df['question'].str.len().mean()) if 'question' in df.columns else 0
        }
        
        return stats


class TrainingDataConverter:
    """학습 데이터 변환기"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def convert_to_alpaca(self, qa_list: List[Dict], output_path: str) -> None:
        """Alpaca 형식 변환"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for qa in qa_list:
                alpaca_format = {
                    "instruction": f"다음 {qa.get('category', '법률')} 관련 질문에 답변해주세요.",
                    "input": qa['question'],
                    "output": qa['answer']
                }
                f.write(json.dumps(alpaca_format, ensure_ascii=False) + '\n')
        
        self.logger.info(f"Alpaca 형식 저장: {output_path}")

    def convert_to_sharegpt(self, qa_list: List[Dict], output_path: str) -> None:
        """ShareGPT 형식 변환"""
        conversations = []
        
        for qa in qa_list:
            conv = {
                "conversations": [
                    {"from": "human", "value": qa['question']},
                    {"from": "assistant", "value": qa['answer']}
                ]
            }
            conversations.append(conv)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"ShareGPT 형식 저장: {output_path}")

    def convert_to_openai(self, qa_list: List[Dict], output_path: str) -> None:
        """OpenAI 형식 변환"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for qa in qa_list:
                openai_format = {
                    "messages": [
                        {"role": "system", "content": "당신은 법률 전문 상담사입니다."},
                        {"role": "user", "content": qa['question']},
                        {"role": "assistant", "content": qa['answer']}
                    ]
                }
                f.write(json.dumps(openai_format, ensure_ascii=False) + '\n')
        
        self.logger.info(f"OpenAI 형식 저장: {output_path}")

    def convert_all_formats(self, input_path: str, output_dir: str) -> None:
        """모든 형식으로 변환"""
        # 데이터 로드
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        qa_list = data.get('qa_pairs', [])
        
        # 각 형식으로 변환
        self.convert_to_alpaca(qa_list, os.path.join(output_dir, "training_alpaca.jsonl"))
        self.convert_to_sharegpt(qa_list, os.path.join(output_dir, "training_sharegpt.json"))
        self.convert_to_openai(qa_list, os.path.join(output_dir, "training_openai.jsonl"))


def main():
    """메인 실행 함수"""
    # 인자 파서
    parser = argparse.ArgumentParser(
        description='법률 PDF QA 데이터셋 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--input_dir', type=str, default='./data',
                        help='PDF 파일 디렉토리')
    parser.add_argument('--output_dir', type=str, default='./output',
                        help='출력 디렉토리')
    parser.add_argument('--questions_per_chunk', type=int, default=3,
                        help='청크당 질문 수')
    parser.add_argument('--model', type=str, default='gpt-4o',
                        help='사용할 모델')
    parser.add_argument('--temperature', type=float, default=0.1,
                        help='모델 temperature')
    
    args = parser.parse_args()
    
    # 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 로거 설정
    logger = setup_logging()
    logger.info("="*60)
    logger.info("법률 PDF QA 데이터셋 생성 시작")
    logger.info("="*60)
    
    # 설정
    config = {
        'model_name': args.model,
        'temperature': args.temperature,
        'questions_per_chunk': args.questions_per_chunk
    }
    
    # 모델 정보 로깅
    logger.info(f"Primary 모델: {config['model_name']}")
    logger.info(f"Fallback 모델: gpt-3.5-turbo")
    logger.info(f"청크당 질문 수: {config['questions_per_chunk']}")
    
    try:
        # pdfs 폴더에서 모든 PDF 파일 찾기
        pdf_directory = "./pdfs"
        pdf_files = []
        
        if os.path.exists(pdf_directory):
            for file in os.listdir(pdf_directory):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(pdf_directory, file))
        
        if not pdf_files:
            logger.error(f"{pdf_directory} 폴더에서 PDF 파일을 찾을 수 없습니다.")
            return
        
        logger.info(f"발견된 PDF 파일: {len(pdf_files)}개")
        
        # 1. QA 생성
        logger.info("\n[1단계] QA 생성")
        generator = LegalQAGenerator(config, logger)
        generator.process_multiple_pdfs(pdf_files)
        
        raw_path = os.path.join(args.output_dir, "qa_dataset_raw.json")
        generator.save_dataset(raw_path)
        
        # 2. 후처리
        logger.info("\n[2단계] 후처리")
        processor = LegalQAProcessor(logger)
        processed_path = os.path.join(args.output_dir, "qa_dataset_processed.json")
        stats = processor.process(raw_path, processed_path)
        
        # 3. 학습 데이터 변환
        logger.info("\n[3단계] 학습 데이터 변환")
        converter = TrainingDataConverter(logger)
        converter.convert_all_formats(processed_path, args.output_dir)
        
        # 최종 통계 출력
        logger.info("\n" + "="*60)
        logger.info("처리 완료!")
        logger.info("="*60)
        logger.info(f"총 QA 쌍: {stats['total']}")
        logger.info("\n카테고리별 분포:")
        for cat, count in stats['by_category'].items():
            logger.info(f"  - {cat}: {count}")
        logger.info(f"\n평균 답변 길이: {stats['avg_answer_length']}자")
        logger.info(f"평균 질문 길이: {stats['avg_question_length']}자")
        
        logger.info(f"\n생성된 파일:")
        logger.info(f"  - {raw_path}")
        logger.info(f"  - {processed_path}")
        logger.info(f"  - {os.path.join(args.output_dir, 'training_*.json(l)')}")
        
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        logger.debug(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

