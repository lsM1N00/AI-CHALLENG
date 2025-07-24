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
DB_USER = os.getenv("DB_USER", "sangmin")
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
def parse_law_into_clauses(full_text: str, filename: str) -> List[Dict[str, Any]]:
    chunks = []
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    law_title = lines[0] if lines else filename.replace(".pdf", "")

    def split_articles(text):
        return re.split(r'(제\d+조(?:의\d+)?)', text)

    def split_hang(text):
        # 항: ①, ②, ...
        return re.split(r'(①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫|⑬|⑭|⑮|⑯|⑰|⑱|⑲|⑳)', text)

    def split_mok(text):
        # 목: 1. 2. ... (줄 맨 앞에 숫자+점+공백)
        return re.split(r'(^|\n)\s*(\d+)\.\s', text)

    # 1. 장이 실제로 있는지 확인
    if re.search(r'\d+장', full_text):
        chapters = re.split(r'(\d+장)', full_text)
        for i in range(1, len(chapters), 2):
            chapter_title = chapters[i].strip()
            chapter_content = chapters[i+1].strip()
            chapter_num_match = re.match(r'(\d+)', chapter_title)
            if not chapter_num_match:
                continue
            chapter_num = chapter_num_match.group(1)
            articles = split_articles(chapter_content)
            for j in range(1, len(articles), 2):
                article_title = articles[j].strip()
                article_content = articles[j+1].strip()
                article_num_match = re.match(r'제(\d+조(?:의\d+)?)', article_title)
                if not article_num_match:
                    continue
                article_num = article_num_match.group(1)
                # 항(①, ②, ...)이 있는지 확인
                hang_split = split_hang(article_content)
                if len(hang_split) > 1:
                    preamble = hang_split[0].strip()
                    clause_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
                                  '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20}
                    for k in range(1, len(hang_split), 2):
                        hang_symbol = hang_split[k]
                        hang_text = hang_split[k+1].strip()
                        hang_num = clause_map.get(hang_symbol, 0)
                        # 목(1. 2. ...)이 있는지 확인
                        mok_split = split_mok(hang_text)
                        if len(mok_split) > 2:
                            for m in range(2, len(mok_split), 2):
                                mok_num = mok_split[m-1]
                                mok_text = mok_split[m].strip()
                                if mok_text:
                                    clause_id = f"{chapter_num}-{article_num}-{hang_num}-{mok_num}"
                                    chunks.append({
                                        "title": law_title,
                                        "chapter_title": chapter_title,
                                        "article_title": article_title,
                                        "chapter": chapter_num,
                                        "article": article_num,
                                        "hang": hang_num,
                                        "mok": mok_num,
                                        "clause_id": clause_id,
                                        "content": f"{chapter_title} {article_title} {hang_symbol} {mok_num}. {mok_text}",
                                        "source_file": filename
                                    })
                        else:
                            # 목이 없으면 항 단위로 저장
                            clause_id = f"{chapter_num}-{article_num}-{hang_num}"
                            if hang_text:
                                chunks.append({
                                    "title": law_title,
                                    "chapter_title": chapter_title,
                                    "article_title": article_title,
                                    "chapter": chapter_num,
                                    "article": article_num,
                                    "hang": hang_num,
                                    "clause_id": clause_id,
                                    "content": f"{chapter_title} {article_title} {hang_symbol} {hang_text}",
                                    "source_file": filename
                                })
                else:
                    # 항이 없고 목(1. 2. ...)이 있는지 확인
                    mok_split = split_mok(article_content)
                    if len(mok_split) > 2:
                        for m in range(2, len(mok_split), 2):
                            mok_num = mok_split[m-1]
                            mok_text = mok_split[m].strip()
                            if mok_text:
                                clause_id = f"{chapter_num}-{article_num}-{mok_num}"
                                chunks.append({
                                    "title": law_title,
                                    "chapter_title": chapter_title,
                                    "article_title": article_title,
                                    "chapter": chapter_num,
                                    "article": article_num,
                                    "mok": mok_num,
                                    "clause_id": clause_id,
                                    "content": f"{chapter_title} {article_title} {mok_num}. {mok_text}",
                                    "source_file": filename
                                })
                    else:
                        # 항/목이 없으면 조 단위로 저장
                        if article_content.strip():
                            clause_id = f"{chapter_num}-{article_num}"
                            chunks.append({
                                "title": law_title,
                                "chapter_title": chapter_title,
                                "article_title": article_title,
                                "chapter": chapter_num,
                                "article": article_num,
                                "clause_id": clause_id,
                                "content": f"{chapter_title} {article_title} {article_content.strip()}",
                                "source_file": filename
                            })
        return chunks

    # 2. 편이 실제로 있는지 확인
    if re.search(r'제\d+편', full_text):
        parts = re.split(r'(제\d+편)', full_text)
        for i in range(1, len(parts), 2):
            part_title = parts[i].strip()
            part_content = parts[i+1].strip()
            part_num_match = re.match(r'제(\d+)편', part_title)
            if not part_num_match:
                continue
            part_num = part_num_match.group(1)
            articles = split_articles(part_content)
            for j in range(1, len(articles), 2):
                article_title = articles[j].strip()
                article_content = articles[j+1].strip()
                article_num_match = re.match(r'제(\d+조(?:의\d+)?)', article_title)
                if not article_num_match:
                    continue
                article_num = article_num_match.group(1)
                hang_split = split_hang(article_content)
                if len(hang_split) > 1:
                    preamble = hang_split[0].strip()
                    clause_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
                                  '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20}
                    for k in range(1, len(hang_split), 2):
                        hang_symbol = hang_split[k]
                        hang_text = hang_split[k+1].strip()
                        hang_num = clause_map.get(hang_symbol, 0)
                        mok_split = split_mok(hang_text)
                        if len(mok_split) > 2:
                            for m in range(2, len(mok_split), 2):
                                mok_num = mok_split[m-1]
                                mok_text = mok_split[m].strip()
                                if mok_text:
                                    clause_id = f"{part_num}-{article_num}-{hang_num}-{mok_num}"
                                    chunks.append({
                                        "title": law_title,
                                        "part_title": part_title,
                                        "article_title": article_title,
                                        "part": part_num,
                                        "article": article_num,
                                        "hang": hang_num,
                                        "mok": mok_num,
                                        "clause_id": clause_id,
                                        "content": f"{part_title} {article_title} {hang_symbol} {mok_num}. {mok_text}",
                                        "source_file": filename
                                    })
                        else:
                            clause_id = f"{part_num}-{article_num}-{hang_num}"
                            if hang_text:
                                chunks.append({
                                    "title": law_title,
                                    "part_title": part_title,
                                    "article_title": article_title,
                                    "part": part_num,
                                    "article": article_num,
                                    "hang": hang_num,
                                    "clause_id": clause_id,
                                    "content": f"{part_title} {article_title} {hang_symbol} {hang_text}",
                                    "source_file": filename
                                })
                else:
                    mok_split = split_mok(article_content)
                    if len(mok_split) > 2:
                        for m in range(2, len(mok_split), 2):
                            mok_num = mok_split[m-1]
                            mok_text = mok_split[m].strip()
                            if mok_text:
                                clause_id = f"{part_num}-{article_num}-{mok_num}"
                                chunks.append({
                                    "title": law_title,
                                    "part_title": part_title,
                                    "article_title": article_title,
                                    "part": part_num,
                                    "article": article_num,
                                    "mok": mok_num,
                                    "clause_id": clause_id,
                                    "content": f"{part_title} {article_title} {mok_num}. {mok_text}",
                                    "source_file": filename
                                })
                    else:
                        if article_content.strip():
                            clause_id = f"{part_num}-{article_num}"
                            chunks.append({
                                "title": law_title,
                                "part_title": part_title,
                                "article_title": article_title,
                                "part": part_num,
                                "article": article_num,
                                "clause_id": clause_id,
                                "content": f"{part_title} {article_title} {article_content.strip()}",
                                "source_file": filename
                            })
        return chunks

    # 3. 장/편이 모두 없으면 바로 조로 분리 (항/목/조)
    articles = split_articles(full_text)
    for i in range(1, len(articles), 2):
        article_title = articles[i].strip()
        article_content = articles[i+1].strip()
        article_num_match = re.match(r'제(\d+조(?:의\d+)?)', article_title)
        if not article_num_match:
            continue
        article_num = article_num_match.group(1)
        hang_split = split_hang(article_content)
        if len(hang_split) > 1:
            preamble = hang_split[0].strip()
            clause_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
                          '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20}
            for k in range(1, len(hang_split), 2):
                hang_symbol = hang_split[k]
                hang_text = hang_split[k+1].strip()
                hang_num = clause_map.get(hang_symbol, 0)
                mok_split = split_mok(hang_text)
                if len(mok_split) > 2:
                    for m in range(2, len(mok_split), 2):
                        mok_num = mok_split[m-1]
                        mok_text = mok_split[m].strip()
                        if mok_text:
                            clause_id = f"{article_num}-{hang_num}-{mok_num}"
                            chunks.append({
                                "title": law_title,
                                "article_title": article_title,
                                "article": article_num,
                                "hang": hang_num,
                                "mok": mok_num,
                                "clause_id": clause_id,
                                "content": f"{article_title} {hang_symbol} {mok_num}. {mok_text}",
                                "source_file": filename
                            })
                else:
                    clause_id = f"{article_num}-{hang_num}"
                    if hang_text:
                        chunks.append({
                            "title": law_title,
                            "article_title": article_title,
                            "article": article_num,
                            "hang": hang_num,
                            "clause_id": clause_id,
                            "content": f"{article_title} {hang_symbol} {hang_text}",
                            "source_file": filename
                        })
        else:
            mok_split = split_mok(article_content)
            if len(mok_split) > 2:
                for m in range(2, len(mok_split), 2):
                    mok_num = mok_split[m-1]
                    mok_text = mok_split[m].strip()
                    if mok_text:
                        clause_id = f"{article_num}-{mok_num}"
                        chunks.append({
                            "title": law_title,
                            "article_title": article_title,
                            "article": article_num,
                            "mok": mok_num,
                            "clause_id": clause_id,
                            "content": f"{article_title} {mok_num}. {mok_text}",
                            "source_file": filename
                        })
            else:
                if article_content.strip():
                    clause_id = f"{article_num}"
                    chunks.append({
                        "title": law_title,
                        "article_title": article_title,
                        "article": article_num,
                        "clause_id": clause_id,
                        "content": f"{article_title} {article_content.strip()}",
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
def insert_document_chunk(conn, chunk: Dict[str, Any], embedding_vector: List[float]):
    """
    분할된 문서 조각과 임베딩 벡터를 'documents' 테이블에 삽입합니다.
    """
    sql = """
    INSERT INTO documents (content, vector, metadata)
    VALUES (%s, %s, %s);
    """
    try:
        with conn.cursor() as cur:
            metadata = {
                "source_file": chunk["source_file"],
                "title": chunk["title"],
                "chapter": chunk.get("chapter"),
                "article": chunk["article"],
                "clause_id": chunk.get("clause_id")
            }
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            cur.execute(sql, (
                chunk["content"],
                embedding_vector,
                metadata_json
            ))
        conn.commit()
        logging.info(f"삽입 완료: {chunk['source_file']} (clause_id: {chunk.get('clause_id', '')})")
    except Exception as e:
        conn.rollback()
        logging.error(f"DB 삽입 오류: {e} - 데이터: {chunk}")

# --- 메인 실행 함수 ---
def main():
    pdf_directory = "./laws_pdfs"
    if not os.path.exists(pdf_directory):
        os.makedirs(pdf_directory)
        logging.warning(f"'{pdf_directory}' 디렉토리를 생성했습니다. PDF 파일을 이 안에 넣어주세요.")
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT,
                vector VECTOR(1024),
                metadata JSONB
            );
            """)
            cur.execute("TRUNCATE TABLE documents RESTART IDENTITY;")
            conn.commit()
            logging.info("Table 'documents' is ready and truncated.")

        for filename in os.listdir(pdf_directory):
            if not filename.lower().endswith(".pdf"):
                continue
            pdf_path = os.path.join(pdf_directory, filename)
            logging.info(f"처리 중: {pdf_path}")

            full_text = extract_text_from_pdf(pdf_path)
            if not full_text:
                logging.warning(f"건너뜀: {filename} (텍스트 추출 실패)")
                continue

            law_chunks = parse_law_into_clauses(full_text, filename)
            logging.info(f"{filename}에서 {len(law_chunks)}개의 조/항을 찾았습니다.")

            for chunk in law_chunks:
                embedding_vector = get_embedding(chunk["content"])
                insert_document_chunk(conn, chunk, embedding_vector)

if __name__ == "__main__":
    main()