import fitz  # PyMuPDF
import psycopg2
from pgvector.psycopg2 import register_vector
import re
import os
import json
import logging
from typing import List, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

# --- 환경변수 로드 ---
load_dotenv()

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# --- 데이터베이스 연결 설정 ---
DB_NAME = os.getenv("DB_NAME", "financedb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "0717")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- BGEM3 임베딩 클래스 정의 ---
class BGEM3Embeddings:
    """BGE-M3 임베딩 클래스"""
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            logger.info(f"BGE-M3 임베딩 모델 로드 완료: {model_name}")
        except Exception as e:
            logger.error(f"BGE-M3 모델 로드 실패: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        try:
            inputs = self.tokenizer([text], padding=True, truncation=True, return_tensors="pt", max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :]
                return embedding[0].cpu().tolist()
        except Exception as e:
            logger.error(f"쿼리 임베딩 실패: {e}")
            return []

# --- 임베딩 모델 인스턴스 전역 생성 ---
bge_embedder = BGEM3Embeddings()

def get_embedding(text: str) -> List[float]:
    """
    주어진 텍스트에 대한 임베딩 벡터를 생성합니다. (BGE-M3 사용)
    """
    return bge_embedder.embed_query(text)

# --- PDF 텍스트 추출 및 정리 함수 ---
def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF 파일에서 텍스트를 추출하고 머리글/바닥글을 정리합니다."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text()
                # 페이지 번호, 법제처, 국가법령정보센터 등 머리글/바닥글 제거
                cleaned_text = re.sub(r'^법제처\s*\d*\s*국가법령정보센터\s*$\n', '', page_text, flags=re.MULTILINE)
                cleaned_text = re.sub(r'^금융소비자 보호에 관한 법률\s*$\n', '', cleaned_text, flags=re.MULTILINE)
                text += cleaned_text
    except Exception as e:
        logging.error(f"텍스트 추출 오류({pdf_path}): {e}")
    return text

# --- 법률 텍스트 파싱 함수 (조/항 단위 분리) ---
def parse_law_into_clauses(text, filename):
    chunks = []
    full_text = text
    
    # 법률 제목 추출
    lines = text.split('\n')
    law_title = lines[0].strip() if lines else filename
    
    def split_articles(text):
        # 조: 제1조, 제2조, ... (공백 허용)
        # 조 제목과 본문이 한 줄에 있는 경우도 처리
        # 참조 패턴은 분리하지 않음 (조사가 붙거나 복합 참조인 경우)
        
        # 1단계: 참조 패턴을 임시 토큰으로 치환
        temp_text = text
        reference_counter = 0
        reference_map = {}
        
        # 복합 참조 패턴들 (제9조제1호, 제8조의4를, 제10조제1항을 등)
        reference_patterns = [
            r'제\d+조(?:의\d+)?제\d+(?:호|항|목)(?:부터\s+제\d+(?:호|항|목)까지)?[를에의와로은는과]',  # 제9조제1호를
            r'제\d+조(?:의\d+)?[를에의와로은는과]',  # 제8조의4를
            r'제\d+조(?:의\d+)?(?:제\d+(?:호|항|목))?부터\s+제\d+(?:호|항|목)까지[를에의와로은는과]?'  # 제9조제2호부터 제7호까지를
        ]
        
        for pattern in reference_patterns:
            matches = re.finditer(pattern, temp_text)
            for match in matches:
                token = f'__REF_TOKEN_{reference_counter}__'
                reference_map[token] = match.group()
                temp_text = temp_text.replace(match.group(), token, 1)
                reference_counter += 1
        
        # 2단계: 실제 조항만 분리 (제목이 있거나 내용이 바로 시작하는 경우)
        pattern = r'(제\s*\d+\s*조(?:의\d+)?(?:\([^)]+\))?)'
        articles = re.split(pattern, temp_text)
        
        # 3단계: 참조 토큰을 원래 텍스트로 복원
        for i, article in enumerate(articles):
            for token, original in reference_map.items():
                articles[i] = articles[i].replace(token, original)
        
        return articles
    
    def split_hang(text):
        # 항: ①, ②, ③, ... 
        hang_symbols = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
        pattern = f'([{hang_symbols}])'
        return re.split(pattern, text)

    def split_ho(text):
        # 호: 1., 2., 3., ... (숫자)
        # "다음 각" 패턴을 활용한 더 안정적인 분할
        # 개정 날짜 패턴은 제외 (예: "개정 2014. 5. 20.")
        
        # 1단계: 개정 날짜 패턴을 임시 토큰으로 보호
        protected_text = text
        amendment_counter = 0
        amendment_map = {}
        
        # 개정 날짜 패턴들
        amendment_patterns = [
            r'<개정\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?>',  # <개정 2014. 5. 20.>
            r'개정\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?',   # 개정 2014. 5. 20.
        ]
        
        for pattern in amendment_patterns:
            matches = re.finditer(pattern, protected_text)
            for match in matches:
                token = f'__AMEND_TOKEN_{amendment_counter}__'
                amendment_map[token] = match.group()
                protected_text = protected_text.replace(match.group(), token, 1)
                amendment_counter += 1
        
        # 2단계: 호 번호 분리 (보호된 텍스트에서)
        ho_split = re.split(r'(?:^|\n)\s*(\d+)\s*\.\s*', protected_text)
        
        # 3단계: 개정 토큰을 원래 텍스트로 복원
        for i, part in enumerate(ho_split):
            for token, original in amendment_map.items():
                ho_split[i] = ho_split[i].replace(token, original)
        
        return ho_split

    def split_mok(text):
        # 목: 가., 나., 다., ... (한글)
        return re.split(r'(?:^|\n)\s*([가-하])\.\s', text)

    def split_gamok(text):
        return re.split(r'(?:^|\n)\s*([가-하])\.\s', text)

    # 부칙과 메인 법률 분리
    if '부칙' in full_text:
        main_text = full_text.split('부칙')[0]
        addendum_text = '부칙' + '부칙'.join(full_text.split('부칙')[1:])
        logging.info(f"메인 법률과 부칙을 분리해서 파싱합니다: {filename}")
    else:
        main_text = full_text
        addendum_text = ""
    
    # 다른 법률 개정 관련 내용 제거 (예: "○○법률 일부를 다음과 같이 개정한다")
    if '일부를 다음과 같이 개정한다' in main_text:
        main_text = main_text.split('일부를 다음과 같이 개정한다')[0]
        logging.info(f"개정 관련 부분을 제외하고 파싱합니다: {filename}")
    
    # 1. 장이 있는 경우 (현재 test.pdf에는 없음)
    if re.search(r'\d+장', main_text):
        # 기존 장 처리 로직 유지하되 새로운 파싱 적용
        pass
    
    # 2. 편이 있는 경우 (현재 test.pdf에는 없음)  
    elif re.search(r'제\d+편', main_text):
        # 기존 편 처리 로직 유지하되 새로운 파싱 적용
        pass
    
    # 3. 조만 있는 경우 (test.pdf의 경우)
    else:
        articles = split_articles(main_text)
        for i in range(1, len(articles), 2):
            if i+1 >= len(articles):
                continue
                
            article_title = articles[i].strip()
            article_content = articles[i+1].strip()
            
            # 2조 원본 텍스트 디버깅
            if "2조" in article_title:
                logging.info(f"=== 2조 원본 텍스트 디버깅 ===")
                logging.info(f"article_title: '{article_title}'")
                logging.info(f"article_content 길이: {len(article_content)}")
                logging.info(f"article_content 전체:\n{article_content}")
                logging.info(f"=== 2조 원본 텍스트 끝 ===")
            
            # 조 번호 추출
            article_num_match = re.match(r'제\s*(\d+\s*조(?:의\d+)?)', article_title)
            if not article_num_match:
                continue
            article_num = article_num_match.group(1).replace(' ', '')
            
            # 먼저 항(①②③)이 있는지 확인
            hang_split = split_hang(article_content)
            if len(hang_split) > 1:
                # 항이 있는 경우
                preamble = hang_split[0].strip()
                hang_num_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
                               '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20}
                
                for k in range(1, len(hang_split), 2):
                    if k+1 >= len(hang_split):
                        continue
                    hang_symbol = hang_split[k]
                    hang_text = hang_split[k+1].strip()
                    hang_num = hang_num_map.get(hang_symbol, 0)
                    
                    # 각 항 내에서 목과 가목 처리
                    processed_chunks = process_ho_and_mok(
                        hang_text, law_title, "", article_title, article_num, hang_num, hang_symbol, filename
                    )
                    chunks.extend(processed_chunks)
            else:
                # 항이 없는 경우 - 바로 호와 목 처리
                processed_chunks = process_ho_and_mok(
                    article_content, law_title, "", article_title, article_num, 0, "", filename
                )
                
                # 만약 목이나 가목으로 분리되지 않은 경우, 조 자체의 메인 내용 저장
                if not processed_chunks or len(processed_chunks) == 0:
                    if article_content.strip():
                        chunks.append({
                            "title": law_title,
                            "chapter_title": "",
                            "article_title": article_title,
                            "chapter": "",
                            "article": article_num,
                            "hang": "",
                            "hang_symbol": "",
                            "mok": "",
                            "gamok": "",
                            "clause_id": article_num,
                            "content": f"{article_title} {article_content.strip()}",
                            "source_file": filename
                        })
                else:
                    chunks.extend(processed_chunks)
    
    # 부칙 파싱
    if addendum_text:
        logging.info(f"부칙 파싱 시작: {filename}")
        addendum_articles = split_articles(addendum_text)
        
        # 개정 관련 내용을 통합하기 위한 변수
        amendment_content = ""
        amendment_article_num = ""
        skip_next = False
        
        for i in range(1, len(addendum_articles), 2):
            if i+1 >= len(addendum_articles):
                continue
                
            article_title = addendum_articles[i].strip()
            article_content = addendum_articles[i+1].strip()
            
            # 이전에 skip 설정된 경우 건너뛰기
            if skip_next:
                # 개정 내용을 이전 조항에 추가
                if amendment_content and article_content:
                    amendment_content += " " + article_content
                continue
            
            # 부칙의 경우 joo = '부칙'으로 설정
            if '부칙' in article_title or i == 1:  # 첫 번째이거나 부칙이 포함된 경우
                article_num = '부칙'
            else:
                # 부칙 내의 조 번호 추출
                article_num_match = re.match(r'제\s*(\d+\s*조(?:의\d+)?)', article_title)
                if article_num_match:
                    article_num = '부칙-' + article_num_match.group(1).replace(' ', '')
                else:
                    article_num = '부칙'
            
            # 개정 패턴 감지
            if '개정한다' in article_content:
                logging.info(f"부칙 개정 패턴 감지: {article_num}")
                # 현재 조항부터 다음 조항까지 모든 내용을 수집
                amendment_content = article_content
                amendment_article_num = article_num
                
                # 다음 조항들의 내용을 현재 조항에 통합
                for j in range(i+2, len(addendum_articles), 2):
                    if j+1 >= len(addendum_articles):
                        break
                    next_title = addendum_articles[j].strip() if j < len(addendum_articles) else ""
                    next_content = addendum_articles[j+1].strip() if j+1 < len(addendum_articles) else ""
                    
                    # 다음 실제 조항(제목이 있는)이 나오기 전까지 내용 수집
                    if next_title and re.match(r'제\s*\d+\s*조', next_title) and '(' in next_title:
                        # 실제 조항 제목이면 중단
                        break
                    else:
                        # 개정 내용이면 추가
                        if next_content:
                            amendment_content += " " + next_content
                        skip_next = True
                
                # 통합된 개정 내용으로 조항 저장
                hang_split = split_hang(amendment_content)
                if len(hang_split) > 1:
                    # 항이 있는 경우
                    preamble = hang_split[0].strip()
                    hang_num_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
                                   '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20}
                    
                    for k in range(1, len(hang_split), 2):
                        if k+1 >= len(hang_split):
                            continue
                        hang_symbol = hang_split[k]
                        hang_text = hang_split[k+1].strip()
                        hang_num = hang_num_map.get(hang_symbol, 0)
                        
                        # 개정 조항은 호와 목으로 분리하지 않고 전체 내용 저장
                        chunks.append({
                            "title": law_title,
                            "chapter_title": "",
                            "article_title": article_title,
                            "chapter": "",
                            "article": amendment_article_num,
                            "hang": str(hang_num) if hang_num > 0 else "",
                            "hang_symbol": hang_symbol if hang_num > 0 else "",
                            "ho": "",
                            "mok": "",
                            "clause_id": f"{amendment_article_num}-{hang_num}" if hang_num > 0 else amendment_article_num,
                            "content": f"{article_title} {hang_symbol} {hang_text}" if hang_symbol else f"{article_title} {hang_text}",
                            "source_file": filename
                        })
                else:
                    # 항이 없는 경우
                    chunks.append({
                        "title": law_title,
                        "chapter_title": "",
                        "article_title": article_title,
                        "chapter": "",
                        "article": amendment_article_num,
                        "hang": "",
                        "hang_symbol": "",
                        "ho": "",
                        "mok": "",
                        "clause_id": amendment_article_num,
                        "content": f"{article_title} {amendment_content}",
                        "source_file": filename
                    })
                
                # 스킵 상태 리셋
                skip_next = False
                amendment_content = ""
                amendment_article_num = ""
                continue
            
            # 일반 부칙 처리 (기존 로직)
            hang_split = split_hang(article_content)
            if len(hang_split) > 1:
                # 항이 있는 경우
                preamble = hang_split[0].strip()
                hang_num_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
                               '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20}
                
                for k in range(1, len(hang_split), 2):
                    if k+1 >= len(hang_split):
                        continue
                    hang_symbol = hang_split[k]
                    hang_text = hang_split[k+1].strip()
                    hang_num = hang_num_map.get(hang_symbol, 0)
                    
                    processed_chunks = process_ho_and_mok(
                        hang_text, law_title, "", article_title, article_num, hang_num, hang_symbol, filename
                    )
                    chunks.extend(processed_chunks)
            else:
                # 항이 없는 경우
                processed_chunks = process_ho_and_mok(
                    article_content, law_title, "", article_title, article_num, 0, "", filename
                )
                
                if not processed_chunks or len(processed_chunks) == 0:
                    if article_content.strip():
                        chunks.append({
                            "title": law_title,
                            "chapter_title": "",
                            "article_title": article_title,
                            "chapter": "",
                            "article": article_num,
                            "hang": "",
                            "hang_symbol": "",
                            "ho": "",
                            "mok": "",
                            "clause_id": article_num,
                            "content": f"{article_title} {article_content.strip()}",
                            "source_file": filename
                        })
                else:
                    chunks.extend(processed_chunks)
    
    return chunks

def process_ho_and_mok(text, law_title, chapter_title, article_title, article_num, hang_num, hang_symbol, filename):
    """호(1,2,3.)와 목(가,나,다.) 처리"""
    chunks = []
    
    def split_ho(text):
        # 호: 1., 2., 3., ... (숫자)
        # "다음 각" 패턴을 활용한 더 안정적인 분할
        # 개정 날짜 패턴은 제외 (예: "개정 2014. 5. 20.")
        
        # 1단계: 개정 날짜 패턴을 임시 토큰으로 보호
        protected_text = text
        amendment_counter = 0
        amendment_map = {}
        
        # 개정 날짜 패턴들
        amendment_patterns = [
            r'<개정\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?>',  # <개정 2014. 5. 20.>
            r'개정\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?',   # 개정 2014. 5. 20.
        ]
        
        for pattern in amendment_patterns:
            matches = re.finditer(pattern, protected_text)
            for match in matches:
                token = f'__AMEND_TOKEN_{amendment_counter}__'
                amendment_map[token] = match.group()
                protected_text = protected_text.replace(match.group(), token, 1)
                amendment_counter += 1
        
        # 2단계: 호 번호 분리 (보호된 텍스트에서)
        ho_split = re.split(r'(?:^|\n)\s*(\d+)\s*\.\s*', protected_text)
        
        # 3단계: 개정 토큰을 원래 텍스트로 복원
        for i, part in enumerate(ho_split):
            for token, original in amendment_map.items():
                ho_split[i] = ho_split[i].replace(token, original)
        
        return ho_split

    def split_mok(text):
        # 목: 가., 나., 다., ... (한글)
        return re.split(r'(?:^|\n)\s*([가-하])\.\s', text)

    def split_gamok(text):
        return re.split(r'(?:^|\n)\s*([가-하])\.\s', text)
    
    # 2조 디버깅을 위한 로그 추가
    if "2조" in article_num:
        logging.info(f"=== 2조 디버깅 시작 ===")
        logging.info(f"입력 텍스트 길이: {len(text)}")
        logging.info(f"입력 텍스트 앞 100자: {text[:100]}")
        
        mok_split_result = split_mok(text)
        logging.info(f"목 분할 결과 개수: {len(mok_split_result)}")
        for i, part in enumerate(mok_split_result[:5]):  # 처음 5개만 출력
            logging.info(f"목 분할 [{i}]: {part[:50]}...")
    
    # 호(1,2,3...)가 있는지 먼저 확인
    ho_split = split_ho(text)
    if len(ho_split) > 1:
        # 호가 있는 경우
        preamble = ho_split[0].strip()
        
        # 2조 디버깅
        if "2조" in article_num:
            logging.info(f"호 분할 결과 개수: {len(ho_split)}")
            logging.info(f"preamble 내용: '{preamble}'")
            logging.info(f"preamble 길이: {len(preamble.strip())}")
        
        # preamble이 있으면 먼저 저장 (메인 조문)
        if preamble and len(preamble.strip()) > 5:
            content_parts = []
            content_parts.append(article_title)
            if hang_symbol:
                content_parts.append(hang_symbol)
            content_parts.append(preamble)
            
            # 2조 디버깅
            if "2조" in article_num:
                logging.info(f"메인 조문 저장: {' '.join(content_parts)[:100]}...")
            
            chunks.append({
                "title": law_title,
                "chapter_title": chapter_title,
                "article_title": article_title,
                "chapter": "",
                "article": article_num,
                "hang": str(hang_num) if hang_num > 0 else "",
                "hang_symbol": hang_symbol if hang_num > 0 else "",
                "ho": "",
                "mok": "",
                "clause_id": f"{article_num}-{hang_num}-main" if hang_num > 0 else f"{article_num}-main",
                "content": " ".join(content_parts),
                "source_file": filename
            })
        
        for h in range(1, len(ho_split), 2):
            if h+1 >= len(ho_split):
                continue
            ho_num = ho_split[h]
            ho_text = ho_split[h+1].strip()
            
            # 2조 디버깅
            if "2조" in article_num:
                logging.info(f"호 번호: {ho_num}, 내용: {ho_text[:50]}...")
            
            if not ho_text:
                continue
                
            # 각 호 내에서 목(가.나.다.) 확인
            mok_split = split_mok(ho_text)
            if len(mok_split) > 1:
                # 목이 있는 경우 - 먼저 호 자체의 preamble 저장
                mok_preamble = mok_split[0].strip()
                if mok_preamble and len(mok_preamble.strip()) > 5:
                    content_parts = []
                    content_parts.append(article_title)
                    if hang_symbol:
                        content_parts.append(hang_symbol)
                    content_parts.append(f"{ho_num}.")
                    content_parts.append(mok_preamble)
                    
                    chunks.append({
                        "title": law_title,
                        "chapter_title": chapter_title,
                        "article_title": article_title,
                        "chapter": "",
                        "article": article_num,
                        "hang": str(hang_num) if hang_num > 0 else "",
                        "hang_symbol": hang_symbol if hang_num > 0 else "",
                        "ho": int(ho_num),
                        "mok": "",
                        "clause_id": f"{article_num}-{hang_num}-{ho_num}" if hang_num > 0 else f"{article_num}-{ho_num}",
                        "content": " ".join(content_parts),
                        "source_file": filename
                    })
                
                # 각 목 저장
                for m in range(1, len(mok_split), 2):
                    if m+1 >= len(mok_split):
                        continue
                    mok_char = mok_split[m]
                    mok_text = mok_split[m+1].strip()
                    
                    if mok_text:
                        content_parts = []
                        content_parts.append(article_title)
                        if hang_symbol:
                            content_parts.append(hang_symbol)
                        content_parts.append(f"{ho_num}.")
                        content_parts.append(f"{mok_char}.")
                        content_parts.append(mok_text)
                        
                        chunks.append({
                            "title": law_title,
                            "chapter_title": chapter_title,
                            "article_title": article_title,
                            "chapter": "",
                            "article": article_num,
                            "hang": str(hang_num) if hang_num > 0 else "",
                            "hang_symbol": hang_symbol if hang_num > 0 else "",
                            "ho": int(ho_num),
                            "mok": mok_char,
                            "clause_id": f"{article_num}-{hang_num}-{ho_num}-{mok_char}" if hang_num > 0 else f"{article_num}-{ho_num}-{mok_char}",
                            "content": " ".join(content_parts),
                            "source_file": filename
                        })
            else:
                # 목이 없는 경우 - 호 단위로 저장
                content_parts = []
                content_parts.append(article_title)
                if hang_symbol:
                    content_parts.append(hang_symbol)
                content_parts.append(f"{ho_num}.")
                content_parts.append(ho_text)
                
                chunks.append({
                    "title": law_title,
                    "chapter_title": chapter_title,
                    "article_title": article_title,
                    "chapter": "",
                    "article": article_num,
                    "hang": str(hang_num) if hang_num > 0 else "",
                    "hang_symbol": hang_symbol if hang_num > 0 else "",
                    "ho": int(ho_num),
                    "mok": "",
                    "clause_id": f"{article_num}-{hang_num}-{ho_num}" if hang_num > 0 else f"{article_num}-{ho_num}",
                    "content": " ".join(content_parts),
                    "source_file": filename
                })
    else:
        # 목이 없는 경우 - 가목(가.나.다.)만 있는지 확인
        gamok_split = split_gamok(text)
        if len(gamok_split) > 1:
            # 가목만 있는 경우
            gamok_preamble = gamok_split[0].strip()
            
            for g in range(1, len(gamok_split), 2):
                if g+1 >= len(gamok_split):
                    continue
                gamok_char = gamok_split[g]
                gamok_text = gamok_split[g+1].strip()
                
                if gamok_text:
                    content_parts = []
                    content_parts.append(article_title)
                    if hang_symbol:
                        content_parts.append(hang_symbol)
                    content_parts.append(f"{gamok_char}.")
                    content_parts.append(gamok_text)
                    
                    chunks.append({
                        "title": law_title,
                        "chapter_title": chapter_title,
                        "article_title": article_title,
                        "chapter": "",
                        "article": article_num,
                        "hang": str(hang_num) if hang_num > 0 else "",
                        "hang_symbol": hang_symbol if hang_num > 0 else "",
                        "mok": "",
                        "gamok": gamok_char,
                        "clause_id": f"{article_num}-{hang_num}-{gamok_char}" if hang_num > 0 else f"{article_num}-{gamok_char}",
                        "content": " ".join(content_parts),
                        "source_file": filename
                    })
        else:
            # 목도 가목도 없는 경우 - 조/항 단위로 저장
            if text.strip():
                content_parts = []
                content_parts.append(article_title)
                if hang_symbol:
                    content_parts.append(hang_symbol)
                content_parts.append(text)
                
                chunks.append({
                    "title": law_title,
                    "chapter_title": chapter_title,
                    "article_title": article_title,
                    "chapter": "",
                    "article": article_num,
                    "hang": str(hang_num) if hang_num > 0 else "",
                    "hang_symbol": hang_symbol if hang_num > 0 else "",
                    "mok": "",
                    "gamok": "",
                    "clause_id": f"{article_num}-{hang_num}" if hang_num > 0 else article_num,
                    "content": " ".join(content_parts),
                    "source_file": filename
                })
    
    return chunks

# --- DB 연결 context manager ---
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        register_vector(conn)
        yield conn
    except Exception as e:
        logging.error(f"DB 연결 오류: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logging.info("DB 연결 종료.")

# --- 데이터베이스 삽입 함수 ---
def insert_document_chunk(cursor, chunk):
    try:
        # chunk에서 필요한 값들 추출
        pyeon = chunk.get("pyeon", "")  # 편 추가
        jang = chunk.get("chapter", "")
        joo = chunk.get("article", "")
        ho_value = chunk.get("ho", "")      # 호: 1,2,3,4,5...
        mok_value = chunk.get("mok", "")    # 목: 가,나,다,라,마...
        
        # hang 처리 - 이미 문자열로 처리됨 ("1", "2", "3" 등)
        hang = chunk.get("hang", "")
        if hang == "":
            hang = None
        
        # ho 처리 - ho 값이 있으면 정수로 변환
        if ho_value:
            ho = int(ho_value)
        else:
            ho = None
        
        # mok 처리 - mok 값 그대로 저장 (가, 나, 다, ...)
        if mok_value:
            mok = mok_value
        else:
            mok = None
        
        context = chunk.get("content", "")
        
        # 벡터 임베딩 생성
        embedding = get_embedding(context)
        
        # 메타데이터 생성
        metadata = {
            "title": chunk.get("title", ""),
            "clause_id": chunk.get("clause_id", ""),
            "source_file": chunk.get("source_file", ""),
            "ho": ho_value,
            "mok": mok_value
        }
        
        # DB에 삽입
        cursor.execute("""
            INSERT INTO laws (pyeon, jang, joo, hang, ho, mok, context, vector, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (pyeon, jang, joo, hang, ho, mok, context, embedding, json.dumps(metadata)))
        
        # 성공 로그 (조 정보만 출력)
        logging.info(f"삽입 완료: {chunk.get('source_file', 'unknown')} - {joo}")
        
    except Exception as e:
        logging.error(f"DB 삽입 오류: {e}")
        logging.error(f"문제가 된 chunk: {chunk}")
        raise

# --- 메인 실행 함수 ---
def main():
    pdf_directory = "./ai-/laws_pdfs"
    if not os.path.exists(pdf_directory):
        logging.warning(f"'{pdf_directory}' 디렉토리를 찾을 수 없습니다.")
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            # 테이블이 없으면 생성
            cur.execute("""
            CREATE TABLE IF NOT EXISTS laws (
                id SERIAL PRIMARY KEY,
                pyeon VARCHAR(100),
                jang VARCHAR(100),
                joo VARCHAR(100),
                hang VARCHAR(100),
                ho INTEGER,
                mok VARCHAR(10),
                context TEXT,
                vector vector(1024),
                metadata JSONB
            );
            """)
            conn.commit()
            logging.info("Table 'laws' is ready.")

            # 모든 PDF 파일 처리
            for filename in os.listdir(pdf_directory):
                if not filename.endswith('.pdf'):
                    continue
                    
                pdf_path = os.path.join(pdf_directory, filename)
                
                if not os.path.exists(pdf_path):
                    logging.error(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
                    continue
                    
                logging.info(f"처리 중: {pdf_path}")

                full_text = extract_text_from_pdf(pdf_path)
                if not full_text:
                    logging.warning(f"건너뜀: {filename} (텍스트 추출 실패)")
                    continue

                law_chunks = parse_law_into_clauses(full_text, filename)
                logging.info(f"{filename}에서 {len(law_chunks)}개의 조/항을 찾았습니다.")

                for chunk in law_chunks:
                    insert_document_chunk(cur, chunk)
            
            conn.commit()

if __name__ == "__main__":
    main()