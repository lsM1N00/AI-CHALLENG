#!/usr/bin/env python3
"""
데이터베이스 및 pgvector 확장 진단 스크립트
"""
import psycopg2
from pgvector.psycopg2 import register_vector
import config
from pdf_to_db import get_embedding

def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        conn = psycopg2.connect(
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        print("✅ 데이터베이스 연결 성공")
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return None

def test_pgvector_extension(conn):
    """pgvector 확장 설치 및 활성화 테스트"""
    try:
        with conn.cursor() as cur:
            # pgvector 확장 설치
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ pgvector 확장 설치/활성화 성공")
            
            # 확장 목록 확인
            cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            result = cur.fetchone()
            if result:
                print(f"✅ pgvector 확장 활성화됨: {result}")
            else:
                print("❌ pgvector 확장이 활성화되지 않음")
            
            # register_vector 등록
            register_vector(conn)
            print("✅ pgvector 타입 등록 성공")
            
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ pgvector 확장 오류: {e}")
        return False

def test_vector_operations(conn):
    """벡터 연산 테스트"""
    try:
        with conn.cursor() as cur:
            # 임시 테스트 테이블 생성
            cur.execute("""
                CREATE TEMP TABLE test_vectors (
                    id SERIAL PRIMARY KEY,
                    vector vector(1024)
                );
            """)
            print("✅ 벡터 테이블 생성 성공")
            
            # 테스트 임베딩 생성
            test_text = "안녕하세요"
            embedding = get_embedding(test_text)
            print(f"✅ 임베딩 생성 성공: 차원={len(embedding)}, 타입={type(embedding)}")
            
            # 벡터 삽입 테스트
            cur.execute("INSERT INTO test_vectors (vector) VALUES (%s);", (embedding,))
            print("✅ 벡터 삽입 성공")
            
            # 유사도 검색 테스트 (벡터 타입 캐스팅 포함)
            cur.execute("""
                SELECT id, vector <=> %s::vector AS distance 
                FROM test_vectors 
                ORDER BY distance 
                LIMIT 1;
            """, (embedding,))
            result = cur.fetchone()
            print(f"✅ 벡터 유사도 검색 성공: {result}")
            
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ 벡터 연산 오류: {e}")
        return False

def test_existing_tables(conn):
    """기존 테이블 구조 확인"""
    try:
        with conn.cursor() as cur:
            tables = ['laws', 'rules', 'terms', 'enfor']
            for table in tables:
                # 테이블 존재 확인
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table,))
                exists = cur.fetchone()[0]
                
                if exists:
                    # 테이블 구조 확인
                    cur.execute("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = 'vector';
                    """, (table,))
                    vector_col = cur.fetchone()
                    
                    # 데이터 개수 확인
                    cur.execute(f"SELECT COUNT(*) FROM {table};")
                    count = cur.fetchone()[0]
                    
                    print(f"✅ 테이블 {table}: 존재함, 벡터컬럼={vector_col}, 데이터={count}개")
                else:
                    print(f"❌ 테이블 {table}: 존재하지 않음")
        return True
    except Exception as e:
        print(f"❌ 테이블 확인 오류: {e}")
        return False

def main():
    """메인 진단 함수"""
    print("🔍 데이터베이스 및 pgvector 진단 시작")
    print("=" * 50)
    
    # 1. 데이터베이스 연결 테스트
    conn = test_database_connection()
    if not conn:
        return
    
    print("\n" + "=" * 50)
    
    # 2. pgvector 확장 테스트
    if not test_pgvector_extension(conn):
        conn.close()
        return
    
    print("\n" + "=" * 50)
    
    # 3. 벡터 연산 테스트
    if not test_vector_operations(conn):
        conn.close()
        return
    
    print("\n" + "=" * 50)
    
    # 4. 기존 테이블 확인
    test_existing_tables(conn)
    
    conn.close()
    print("\n🎉 진단 완료!")

if __name__ == "__main__":
    main() 