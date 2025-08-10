#!/usr/bin/env python3
"""
금융꿀팅, 소비자경보 및 금융뉴스 PDF QA 데이터셋 생성 시스템
Financial Tips, Consumer Alert and Financial News PDF QA Dataset Generation System
"""

import os
import sys
import json
import logging
import argparse
import traceback
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import hashlib
import io
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

# 이미지/OCR 처리
try:
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR 기능을 사용하려면 pytesseract, Pillow, PyMuPDF를 설치하세요: pip install pytesseract Pillow PyMuPDF")

# 유사도 검사
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 환경 변수 로드
load_dotenv()

# NLTK 데이터 자동 다운로드
def setup_nltk():
    """NLTK 데이터 설정"""
    try:
        import nltk
        # 필요한 NLTK 데이터 다운로드
        required_packages = ['punkt', 'punkt_tab']
        for package in required_packages:
            try:
                nltk.data.find(f'tokenizers/{package}')
            except LookupError:
                print(f"NLTK {package} 데이터 다운로드 중...")
                nltk.download(package, quiet=True)
                print(f"NLTK {package} 데이터 다운로드 완료")
    except Exception as e:
        print(f"NLTK 설정 중 오류: {e}")

# NLTK 설정 실행
setup_nltk()

def check_disk_space(path: str, required_gb: float = 1.0) -> bool:
    """디스크 공간 확인"""
    try:
        total, used, free = shutil.disk_usage(path)
        free_gb = free / (1024**3)
        return free_gb >= required_gb
    except Exception as e:
        print(f"디스크 공간 확인 오류: {e}")
        return True  # 확인 실패 시 진행

def cleanup_old_files(directory: str, max_files: int = 10) -> None:
    """오래된 파일 정리"""
    try:
        if not os.path.exists(directory):
            return
        
        # JSON 파일들 찾기
        json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
        log_files = [f for f in os.listdir(directory) if f.endswith('.log')]
        
        # 파일 수가 제한을 초과하면 오래된 파일 삭제
        all_files = json_files + log_files
        if len(all_files) > max_files:
            # 파일 수정 시간 기준으로 정렬
            file_times = []
            for file in all_files:
                file_path = os.path.join(directory, file)
                try:
                    mtime = os.path.getmtime(file_path)
                    file_times.append((file_path, mtime))
                except:
                    continue
            
            # 오래된 순서로 정렬
            file_times.sort(key=lambda x: x[1])
            
            # 오래된 파일들 삭제
            files_to_delete = file_times[:-max_files]
            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                    print(f"오래된 파일 삭제: {os.path.basename(file_path)}")
                except:
                    continue
    except Exception as e:
        print(f"파일 정리 오류: {e}")

# 로깅 설정
def setup_logging(log_dir: str = "./logs") -> logging.Logger:
    """로깅 설정"""
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"financial_tips_qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    # 로거 설정
    logger = logging.getLogger('FinancialTipsQA')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
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


class FinancialTipsQAGenerator:
    """금융꿀팅, 소비자경보 및 금융뉴스 QA 생성기"""
    
    def __init__(self, config: dict, logger: logging.Logger, output_dir: str = "./output"):
        self.config = config
        self.logger = logger
        self.output_dir = output_dir
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
        
        # 강제 OCR 옵션이 있으면 바로 OCR 시도
        if self.config.get('force_ocr', False):
            self.logger.info(f"강제 OCR 모드: {filepath}")
            return self.try_ocr_parsing(filepath)
        
        # 먼저 텍스트 추출 가능성 확인
        text_extraction_success = self.try_text_extraction(filepath)
        
        if text_extraction_success:
            # 텍스트 추출이 성공한 경우, 일반 파싱 시도
            return self.try_standard_parsing(filepath)
        else:
            # 텍스트 추출이 실패한 경우, OCR 시도
            return self.try_ocr_parsing(filepath)
    
    def try_text_extraction(self, filepath: str) -> bool:
        """텍스트 추출 가능성 확인"""
        try:
            import PyPDF2
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_text = ""
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        total_text += text
                
                # 텍스트가 충분히 있는지 확인 (최소 100자)
                if len(total_text.strip()) > 100:
                    self.logger.info(f"텍스트 추출 가능 확인: {len(total_text)}자")
                    return True
                else:
                    self.logger.info(f"텍스트 추출 불가능: {len(total_text)}자")
                    return False
        except Exception as e:
            self.logger.warning(f"텍스트 추출 확인 실패: {e}")
            return False
    
    def try_standard_parsing(self, filepath: str) -> List:
        """일반 PDF 파싱 시도"""
        # 여러 방법으로 PDF 파싱 시도
        methods = [
            # 방법 1: 기본 설정
            {
                "extract_images_in_pdf": False,
                "infer_table_structure": True,
                "chunking_strategy": "by_title",
                "max_characters": 4000,
                "new_after_n_chars": 3800,
                "combine_text_under_n_chars": 2000,
                "languages": ["kor", "eng"],
                "size": {"longest_edge": 2048},
            },
            # 방법 2: 이미지 추출 비활성화, 더 보수적인 설정
            {
                "extract_images_in_pdf": False,
                "infer_table_structure": False,
                "chunking_strategy": "by_title",
                "max_characters": 2000,
                "new_after_n_chars": 1800,
                "combine_text_under_n_chars": 1000,
                "languages": ["kor", "eng"],
                "size": {"longest_edge": 1024},
            },
            # 방법 3: 최소한의 설정
            {
                "extract_images_in_pdf": False,
                "infer_table_structure": False,
                "chunking_strategy": "by_title",
                "max_characters": 1000,
                "new_after_n_chars": 800,
                "combine_text_under_n_chars": 500,
                "languages": ["kor"],
                "size": {"longest_edge": 512},
            },
            # 방법 4: 이미지 완전 비활성화
            {
                "extract_images_in_pdf": False,
                "infer_table_structure": False,
                "chunking_strategy": "by_title",
                "max_characters": 500,
                "new_after_n_chars": 400,
                "combine_text_under_n_chars": 200,
                "languages": ["kor"],
                "size": {"longest_edge": 256},
            },
            # 방법 5: 텍스트만 추출
            {
                "extract_images_in_pdf": False,
                "infer_table_structure": False,
                "chunking_strategy": "by_title",
                "max_characters": 300,
                "new_after_n_chars": 250,
                "combine_text_under_n_chars": 100,
                "languages": ["kor"],
                "size": {"longest_edge": 128},
            }
        ]
        
        for i, method in enumerate(methods):
            try:
                self.logger.info(f"일반 파싱 시도 {i+1}/{len(methods)}: {filepath}")
                elements = partition_pdf(
                    filename=filepath,
                    **method
                )
                self.logger.info(f"추출된 요소 수: {len(elements)}")
                return elements
                
            except Exception as e:
                error_msg = str(e).lower()
                self.logger.warning(f"일반 파싱 시도 {i+1} 실패: {e}")
                
                # 특정 오류의 경우 다음 방법으로 진행
                if any(keyword in error_msg for keyword in [
                    "truncated", "corrupted", "damaged", "invalid", 
                    "image", "file", "format", "size", "bytes not processed"
                ]):
                    self.logger.warning(f"이미지/파일 오류로 다음 방법 시도: {e}")
                    continue
                else:
                    # 다른 오류의 경우 OCR로 전환
                    self.logger.warning(f"일반 파싱 실패, OCR로 전환: {e}")
                    return self.try_ocr_parsing(filepath)
        
        # 모든 일반 파싱이 실패한 경우 OCR로 전환
        self.logger.warning(f"모든 일반 파싱 방법 실패, OCR로 전환: {filepath}")
        return self.try_ocr_parsing(filepath)
    
    def try_ocr_parsing(self, filepath: str) -> List:
        """OCR 파싱 시도"""
        if not OCR_AVAILABLE:
            self.logger.error("OCR 라이브러리가 설치되지 않았습니다.")
            return []
        
        try:
            self.logger.info(f"OCR로 이미지 텍스트 추출 시도: {filepath}")
            ocr_text = self.extract_text_with_ocr(filepath)
            if ocr_text.strip():
                self.logger.info(f"OCR 텍스트 추출 성공: {len(ocr_text)}자")
                # 간단한 텍스트 청크로 분할
                chunks = [ocr_text[i:i+1000] for i in range(0, len(ocr_text), 800)]
                return chunks
            else:
                self.logger.error(f"OCR 텍스트 추출 실패: 빈 텍스트")
                return []
        except Exception as e:
            self.logger.error(f"OCR 파싱 실패: {e}")
            return []
    
    def extract_text_with_ocr(self, filepath: str) -> str:
        """OCR을 사용하여 PDF에서 텍스트 추출"""
        try:
            # PyMuPDF로 PDF 열기
            doc = fitz.open(filepath)
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # 페이지를 이미지로 변환
                mat = fitz.Matrix(2, 2)  # 2배 확대
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # PIL Image로 변환
                img = Image.open(io.BytesIO(img_data))
                
                # OCR 수행 (한국어 + 영어)
                text = pytesseract.image_to_string(img, lang='kor+eng')
                text_content += text + "\n"
            
            doc.close()
            return text_content
            
        except Exception as e:
            self.logger.error(f"OCR 텍스트 추출 오류: {e}")
            return ""
    
    def detect_document_type(self, text: str, filename: str) -> str:
        """문서 유형 감지"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # 파일명 기반 감지
        if any(keyword in filename_lower for keyword in ["꿀팅", "꿀팁", "tips"]):
            return "financial_tips"  # 금융꿀팅
        elif any(keyword in filename_lower for keyword in ["경보", "alert", "주의"]):
            return "consumer_alert"  # 소비자경보
        elif any(keyword in filename_lower for keyword in ["뉴스", "news", "기사", "보도"]):
            return "financial_news"  # 금융뉴스
        
        # 내용 기반 감지
        if any(keyword in text_lower for keyword in ["꿀팁", "팁", "tip", "조언", "가이드", "방법"]):
            return "financial_tips"
        elif any(keyword in text_lower for keyword in ["경보", "주의", "alert", "위험", "사기", "피해"]):
            return "consumer_alert"
        elif any(keyword in text_lower for keyword in ["뉴스", "news", "기사", "보도", "발표", "공시", "실적"]):
            return "financial_news"
        else:
            return "general"  # 일반 금융 문서
    
    def detect_financial_category(self, text: str) -> str:
        """금융 카테고리 감지"""
        categories = {
            "대출": ["대출", "융자", "이자", "연체", "담보", "저당", "신용대출", "주택담보대출"],
            "카드": ["카드", "신용카드", "체크카드", "결제", "할부", "리볼빙", "현금서비스"],
            "예금": ["예금", "적금", "정기예금", "통장", "입출금", "이자율", "금리"],
            "투자": ["펀드", "투자", "증권", "주식", "채권", "손실", "수익률", "리스크"],
            "보험": ["보험", "보험금", "보험료", "약관", "보장", "특약", "생명보험", "손해보험"],
            "연금": ["연금", "퇴직연금", "개인연금", "국민연금", "IRP"],
            "P2P": ["P2P", "대부", "투자", "이자", "리스크"],
            "가상화폐": ["가상화폐", "암호화폐", "비트코인", "이더리움", "코인"],
            "금융정책": ["정책", "규제", "감독", "금융위원회", "금감원", "법률", "개정"],
            "금융시장": ["시장", "환율", "금리", "주가", "부동산", "경제", "인플레이션"],
            "금융회사": ["은행", "증권사", "보험사", "카드사", "금융회사", "기업", "실적"],
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
    
    def create_qa_prompt(self, doc_type: str = "financial_tips") -> PromptTemplate:
        """문서 유형에 따른 프롬프트 생성"""
        
        base_instruction = """당신은 금융 전문가입니다. 주어진 금융 관련 내용을 바탕으로 
일반 소비자들이 실제로 궁금해할 만한 실용적인 질문과 답변을 생성해주세요.

중요: 질문과 답변에서 반드시 구체적인 금융 정보의 핵심 내용을 포함해야 합니다.
"이러한", "해당", "유사한" 처럼 애매모호한 표현 대신 구체적인 내용을 명시하세요.
Context에서 언급된 실제 금융 내용을 그대로 사용하여 구체적으로 언급해야 합니다.

Context:
{context}

카테고리: {category}
"""
        
        if doc_type == "financial_tips":
            # 금융꿀팅용 프롬프트
            specific_instruction = """
이것은 금융꿀팁 문서입니다. Context에서 제시된 구체적인 꿀팁 내용을 그대로 활용하여 QA를 생성하세요:

1. Context에서 제시된 구체적인 꿀팁의 제목이나 주제를 질문으로 변환
2. Context에서 나온 구체적인 팁 내용(번호, 수치, 비율, 절차 등)을 그대로 답변에 포함
3. Context의 구체적인 체크포인트나 단계별 가이드를 그대로 보존
4. Context에서 언급된 구체적인 수치(%, %p, 원 등)를 정확히 포함
5. Context의 구체적인 상황별 대응 방법을 그대로 유지
6. Context에서 제시된 구체적인 주의사항이나 팁을 그대로 포함
7. Context의 구체적인 확인 방법이나 절차를 그대로 보존
8. Context에서 언급된 구체적인 서비스명이나 플랫폼명을 그대로 포함
9. Context에서 언급된 꿀팁에 대한 내용은 무조건 사용하여야 합니다.

중요: Context에서 제시된 구체적인 꿀팁 내용(번호, 수치, 비율, 절차, 체크포인트 등)을 그대로 답변에 포함해야 합니다.
예시:
- 질문: "운전자를 위한 금융꿀팁은 뭐가있나요?"
- 답변: "① 음주·무면허·과로·과속운전 시 과실비율 20%p 가중, ② 어린이·노인·장애인 보호구역내 사고 시 과실비율 15%p 가중, ③ 운전 중 휴대폰, DMB 시청 시 과실비율 10%p 가중, ④ 과실비율 분쟁예방 위해 사진 등 객관적 자료 확보, ⑤ 다양한 사고상황의 과실비율 궁금할 땐「파인」통해 확인"

각 질문은 Context의 꿀팁 주제를 질문으로 변환하고, 답변에는 Context의 구체적인 팁 내용을 그대로 포함해야 합니다.
"""
        elif doc_type == "consumer_alert":
            # 소비자경보용 프롬프트
            specific_instruction = """
이것은 소비자경보/주의사항 문서입니다. 다음 사항에 중점을 두어 {num_questions}개의 질문을 생성하세요:

1. Context에 나온 구체적인 금융 위험 요소와 사기 수법
2. 소비자가 주의해야 할 금융 사기와 피해 방지 방법
3. 금융 상품 가입 시 확인해야 할 중요 사항
4. 금융 소비자 권리 보호와 대응 절차
5. 금융 분쟁 발생 시 구체적인 대처 방법
6. 안전한 금융 거래를 위한 체크리스트
7. 금융 소비자 보호 관련 법적 근거
8. 금융 피해 예방을 위한 실용적인 가이드

각 질문은 실제 일반 소비자가 궁금해할 만한 구체적인 내용이어야 하며, 
Context에서 언급된 실제 금융 내용을 그대로 사용하여 구체적으로 언급해야 합니다.
답변에는 반드시 구체적인 대응 방법, 주의사항, 피해 방지책을 포함해야 합니다.
"""
        elif doc_type == "financial_news":
            # 금융뉴스용 프롬프트
            specific_instruction = """
이것은 금융뉴스/기사 문서입니다. 다음 사항에 중점을 두어 {num_questions}개의 질문을 생성하세요:

1. Context에 나온 구체적인 금융 뉴스의 핵심 내용과 의미
2. 해당 뉴스가 일반 소비자에게 미치는 영향과 시사점
3. 뉴스에서 언급된 금융 정책이나 제도의 변화 내용
4. 금융 시장 동향과 투자 환경 변화에 대한 분석
5. 금융회사나 금융 상품 관련 주요 소식과 그 의미
6. 금융 규제나 정책 변화가 소비자에게 미치는 영향
7. 금융 시장의 위험 요소와 기회 요인 분석
8. 일반 소비자가 알아야 할 금융 시장 동향과 대응 방안

각 질문은 실제 일반 소비자가 궁금해할 만한 구체적인 내용이어야 하며, 
Context에서 언급된 실제 뉴스 내용을 그대로 사용하여 구체적으로 언급해야 합니다.
답변에는 반드시 구체적인 시사점, 영향 분석, 대응 방안을 포함해야 합니다.
"""
        else:
            # 일반 금융 문서용 프롬프트
            specific_instruction = """
이것은 일반 금융 문서입니다. 다음 사항에 중점을 두어 {num_questions}개의 질문을 생성하세요:

1. Context에 나온 구체적인 금융 내용과 의미
2. 일반 소비자가 알아야 할 금융 지식
3. 금융 상품 이용 시 주의사항
4. 금융 소비자 권리와 보호 방안
5. 안전한 금융 거래 방법
6. 금융 분쟁 예방과 대응 방법
7. 금융 계획 수립과 관리 방법
8. 실용적인 금융 정보 활용법

각 질문은 실무적이고 구체적이어야 하며, 
Context에서 언급된 실제 금융 내용을 그대로 사용하여 구체적으로 언급해야 합니다.
답변에는 반드시 구체적인 적용 방법, 주의사항, 실무 팁을 포함해야 합니다.
"""
        
        format_instruction = """
반드시 아래 JSON 형식으로 응답하세요:
```json
{{
    "category": "{category}",
    "question": "구체적이고 실용적인 질문 (금융 내용의 핵심 포함)",
    "answer": "상세하고 실무적인 답변 (최소 100자 이상, 구체적인 금융 내용 포함)"
}},
{{
    "category": "{category}",
    "question": "또 다른 구체적인 질문",
    "answer": "또 다른 상세한 답변"
}}
중요:

모든 질문과 답변은 한국어로 작성
답변은 구체적이고 실용적이어야 함
Context에서 언급된 실제 금융 내용(구체적인 수치, 비율, 절차, 체크포인트 등)을 그대로 사용하여 구체적으로 언급해야 함
법적 근거가 있다면 포함
실제 행동 지침과 체크포인트 포함
"이러한", "해당", "유사한" 등의 모호한 표현 대신 Context의 실제 내용을 명시
답변에는 반드시 구체적인 적용 방법, 주의사항, 실무 팁, 체크포인트를 포함해야 함
특히 금융꿀팁의 경우, Context의 구체적인 팁 내용(번호, 수치, 비율, 절차 등)을 그대로 답변에 포함해야 함 """
        
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
            self.logger.warning(f"PDF 요소 추출 실패: {filepath}")
            return 0
  
        # 문서 유형 감지
        full_text = " ".join([str(el) for el in elements[:10]])  # 처음 10개 요소로 판단
        doc_type = self.detect_document_type(full_text, os.path.basename(filepath))
        self.logger.info(f"문서 유형: {doc_type}")
        
        # 각 청크 처리
        qa_count = 0
        
        # elements가 리스트인지 문자열 리스트인지 확인
        if isinstance(elements, list) and len(elements) > 0:
            if hasattr(elements[0], 'text'):
                # unstructured 요소인 경우
                valid_chunks = [el for el in elements if hasattr(el, 'text') and len(str(el.text)) > 50]
            else:
                # 문자열 리스트인 경우 (PyPDF2 결과)
                valid_chunks = [el for el in elements if isinstance(el, str) and len(el.strip()) > 50]
        else:
            valid_chunks = []
        
        if not valid_chunks:
            self.logger.warning(f"유효한 텍스트 청크가 없음: {filepath}")
            return 0
        
        self.logger.info(f"처리할 청크 수: {len(valid_chunks)}")
        
        with tqdm(total=len(valid_chunks), desc="청크 처리") as pbar:
            for idx, chunk in enumerate(valid_chunks):
                try:
                    # chunk가 요소 객체인지 문자열인지 확인
                    if hasattr(chunk, 'text'):
                        chunk_text = str(chunk.text)
                    else:
                        chunk_text = str(chunk)
                    
                    category = self.detect_financial_category(chunk_text)
                    
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
                    
                except Exception as e:
                    self.logger.error(f"청크 처리 오류 (청크 {idx}): {e}")
                    continue
                
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
                # 디스크 공간 확인
                if not check_disk_space(self.output_dir, required_gb=self.config.get('min_disk_space', 1.0)):
                    self.logger.warning(f"디스크 공간 부족! 출력 디렉토리: {self.output_dir}")
                    # 오래된 파일 정리
                    cleanup_old_files(self.output_dir, max_files=self.config.get('max_files', 10))
                    if not check_disk_space(self.output_dir, required_gb=self.config.get('min_disk_space', 1.0)):
                        self.logger.error("디스크 공간이 부족하여 처리를 중단합니다.")
                        break
                
                count = self.process_pdf(pdf_file, self.config.get('questions_per_chunk', 2))
                total_qa += count
                
                # 체크포인트 저장 (10개 파일마다)
                if (i + 1) % checkpoint_interval == 0:
                    checkpoint_path = os.path.join(self.output_dir, f"qa_checkpoint_{i+1}.json")
                    self.save_dataset(checkpoint_path)
                    self.logger.info(f"체크포인트 저장: {checkpoint_path} (처리된 파일: {i+1}/{len(pdf_files)})")
            else:
                self.logger.warning(f"파일을 찾을 수 없음: {pdf_file}")
        
        self.logger.info(f"\n총 처리 파일: {len(self.processed_files)}")
        self.logger.info(f"총 생성 QA: {total_qa}")
    
    def save_dataset(self, output_path: str) -> None:
        """데이터셋 저장"""
        # 디스크 공간 확인
        output_dir = os.path.dirname(output_path)
        min_space = self.config.get('min_disk_space', 1.0) * 0.5  # 저장 시에는 절반만 필요
        if not check_disk_space(output_dir, required_gb=min_space):
            self.logger.warning(f"저장 전 디스크 공간 부족! 디렉토리: {output_dir}")
            # 오래된 파일 정리
            cleanup_old_files(output_dir, max_files=self.config.get('max_files', 10))
            if not check_disk_space(output_dir, required_gb=min_space):
                self.logger.error("디스크 공간이 부족하여 저장을 건너뜁니다.")
                return
        
        output_data = {
            "metadata": {
                "total_pairs": len(self.qa_pairs),
                "processed_files": len(self.processed_files),
                "generation_date": datetime.now().isoformat(),
                "config": self.config
            },
            "qa_pairs": self.qa_pairs
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"데이터셋 저장: {output_path}")
        except Exception as e:
            self.logger.error(f"데이터셋 저장 실패: {e}")
            # 백업 경로로 저장 시도
            backup_path = os.path.join(self.output_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                self.logger.info(f"백업 파일로 저장: {backup_path}")
            except Exception as backup_e:
                self.logger.error(f"백업 저장도 실패: {backup_e}")


def main():
    """메인 실행 함수"""
    # NLTK 데이터 재확인
    try:
        import nltk
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError as e:
        print(f"NLTK 데이터 누락: {e}")
        print("NLTK 데이터를 다시 다운로드합니다...")
        setup_nltk()
    
    # 인자 파서
    parser = argparse.ArgumentParser(
        description='금융꿀팅, 소비자경보 및 금융뉴스 PDF QA 데이터셋 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 사용법
  python financial_qa_generator.py --output_dir /path/to/output

  # 디스크 공간 관리와 함께 사용
  python financial_qa_generator.py --output_dir /path/to/output --min_disk_space 2.0 --max_files 5

  # 로그 디렉토리 별도 지정
  python financial_qa_generator.py --output_dir /path/to/output --log_dir /path/to/logs

  # 모든 옵션 사용
  python financial_qa_generator.py \\
    --input_dir ./pdfs \\
    --output_dir /path/to/output \\
    --log_dir /path/to/logs \\
    --questions_per_chunk 2 \\
    --model gpt-4o \\
    --temperature 0.1 \\
    --min_disk_space 1.5 \\
    --max_files 8 \\
    --force_ocr
        """
    )
    
    parser.add_argument('--input_dir', type=str, default='./pdfs',
                        help='PDF 파일 디렉토리')
    parser.add_argument('--output_dir', type=str, default='./output',
                        help='출력 디렉토리')
    parser.add_argument('--log_dir', type=str, default=None,
                        help='로그 디렉토리 (기본: output_dir/logs)')
    parser.add_argument('--questions_per_chunk', type=int, default=1,
                        help='청크당 질문 수')
    parser.add_argument('--model', type=str, default='gpt-4o',
                        help='사용할 모델')
    parser.add_argument('--temperature', type=float, default=0.1,
                        help='모델 temperature')
    parser.add_argument('--force_ocr', action='store_true',
                        help='모든 PDF를 OCR로 처리 (기본: 자동 감지)')
    parser.add_argument('--min_disk_space', type=float, default=1.0,
                        help='최소 필요 디스크 공간 (GB)')
    parser.add_argument('--max_files', type=int, default=10,
                        help='최대 보관 파일 수 (오래된 파일 자동 삭제)')
    
    args = parser.parse_args()
    
    # 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 디스크 공간 확인
    if not check_disk_space(args.output_dir, required_gb=args.min_disk_space):
        print(f"경고: 출력 디렉토리 {args.output_dir}의 디스크 공간이 부족합니다.")
        print("오래된 파일을 정리합니다...")
        cleanup_old_files(args.output_dir, max_files=args.max_files)
        if not check_disk_space(args.output_dir, required_gb=args.min_disk_space):
            print("오류: 디스크 공간이 부족하여 프로그램을 종료합니다.")
            return
    
    # 로거 설정 (사용자가 지정한 출력 디렉토리 사용)
    if args.log_dir:
        log_dir = args.log_dir
    else:
        log_dir = os.path.join(args.output_dir, "logs")
    
    os.makedirs(log_dir, exist_ok=True)
    logger = setup_logging(log_dir)
    logger.info("="*60)
    logger.info("금융꿀팅, 소비자경보 및 금융뉴스 PDF QA 데이터셋 생성 시작")
    logger.info("="*60)
    logger.info(f"출력 디렉토리: {args.output_dir}")
    logger.info(f"로그 디렉토리: {log_dir}")
    logger.info(f"최소 필요 디스크 공간: {args.min_disk_space}GB")
    logger.info(f"최대 보관 파일 수: {args.max_files}")
    
    # 설정
    config = {
        'model_name': args.model,
        'temperature': args.temperature,
        'questions_per_chunk': args.questions_per_chunk,
        'force_ocr': args.force_ocr,
        'min_disk_space': args.min_disk_space,
        'max_files': args.max_files
    }
    
    # 모델 정보 로깅
    logger.info(f"Primary 모델: {config['model_name']}")
    logger.info(f"Fallback 모델: gpt-3.5-turbo")
    logger.info(f"청크당 질문 수: {config['questions_per_chunk']}")
    logger.info(f"강제 OCR: {config['force_ocr']}")
    if OCR_AVAILABLE:
        logger.info("OCR 라이브러리 사용 가능 (자동 감지)")
    else:
        logger.warning("OCR 라이브러리가 설치되지 않았습니다. 이미지 PDF 처리가 제한됩니다.")
    
    try:
        # pdfs 폴더에서 모든 PDF 파일 찾기
        pdf_directory = args.input_dir
        pdf_files = []
        
        if os.path.exists(pdf_directory):
            for file in os.listdir(pdf_directory):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(pdf_directory, file))
        
        if not pdf_files:
            logger.error(f"{pdf_directory} 폴더에서 PDF 파일을 찾을 수 없습니다.")
            return
        
        logger.info(f"발견된 PDF 파일: {len(pdf_files)}개")
        
        # QA 생성
        logger.info("\n[1단계] QA 생성")
        generator = FinancialTipsQAGenerator(config, logger, args.output_dir)
        generator.process_multiple_pdfs(pdf_files)
        
        raw_path = os.path.join(args.output_dir, "financial_tips_qa_raw.json")
        generator.save_dataset(raw_path)
        
        # 최종 통계 출력
        logger.info("\n" + "="*60)
        logger.info("처리 완료!")
        logger.info("="*60)
        logger.info(f"총 QA 쌍: {len(generator.qa_pairs)}")
        logger.info(f"총 처리 파일: {len(generator.processed_files)}")
        
        logger.info(f"\n생성된 파일:")
        logger.info(f"  - {raw_path}")
        
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        logger.debug(traceback.format_exc())
        raise


if __name__ == "__main__":
    main() 