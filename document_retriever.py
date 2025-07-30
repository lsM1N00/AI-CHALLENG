"""
문서 검색 모듈 - RAG(Retrieval Augmented Generation)를 위한 문서 검색
"""
import psycopg2
from pgvector.psycopg2 import register_vector
from typing import List, Dict, Any
import config
from pdf_to_db import get_embedding

class DocumentRetriever:
    """문서 검색을 위한 클래스"""
    
    def __init__(self):
        """문서 검색기 초기화"""
        self.conn = None
        self._connect_to_database()
    
    def _connect_to_database(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT
            )
            register_vector(self.conn)
            print("문서 데이터베이스 연결 성공")
            
        except psycopg2.OperationalError as e:
            print(f"데이터베이스 연결 실패: {e}")
            self.conn = None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        쿼리와 유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수
            
        Returns:
            검색된 문서 리스트
        """
        if not self.conn:
            print(" 데이터베이스 연결이 없어 문서 검색을 건너뜁니다.")
            return []

        try:
            # 1. 쿼리를 임베딩으로 변환
            query_embedding = get_embedding(query)
            if not query_embedding:
                print(" 쿼리 임베딩 생성 실패")
                return []

            # 2. 유사도 검색 수행 (모든 테이블에서 검색)
            sql = """
            SELECT id, context as content, metadata, 1 - (vector <=> %s::vector) AS similarity, 'laws' as table_name
            FROM laws
            UNION ALL
            SELECT id, context as content, metadata, 1 - (vector <=> %s::vector) AS similarity, 'rules' as table_name
            FROM rules
            UNION ALL
            SELECT id, context as content, metadata, 1 - (vector <=> %s::vector) AS similarity, 'terms' as table_name
            FROM terms
            UNION ALL
            SELECT id, context as content, metadata, 1 - (vector <=> %s::vector) AS similarity, 'enfor' as table_name
            FROM enfor
            ORDER BY similarity DESC
            LIMIT %s;
            """
            
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (query_embedding, query_embedding, query_embedding, query_embedding, top_k))
                results = cursor.fetchall()
                
                documents = []
                for row in results:
                    documents.append({
                        "id": row[0],
                        "content": row[1],
                        "metadata": row[2],
                        "similarity": float(row[3]),
                        "table_name": row[4]
                    })
                
                print(f"📚 문서 검색 완료: {len(documents)}개 결과")
                return documents
                
        except Exception as e:
            print(f"❌ 문서 검색 오류: {e}")
            return []
    
    def get_document_stats(self) -> Dict[str, int]:
        """데이터베이스 문서 통계"""
        if not self.conn:
            return {"total_documents": 0, "laws": 0, "rules": 0, "terms": 0, "enfor": 0}
        
        try:
            with self.conn.cursor() as cursor:
                stats = {}
                tables = ['laws', 'rules', 'terms', 'enfor']
                total = 0
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        stats[table] = count
                        total += count
                    except Exception:
                        stats[table] = 0
                
                stats["total_documents"] = total
                return stats
        except Exception as e:
            print(f"통계 조회 실패: {e}")
            return {"total_documents": 0, "laws": 0, "rules": 0, "terms": 0, "enfor": 0}
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("📚 문서 검색기 연결 종료")

if __name__ == '__main__':
    # 테스트 실행
    retriever = DocumentRetriever()
    
    # 통계 출력
    stats = retriever.get_document_stats()
    print(f"데이터베이스 문서 수:")
    print(f"  총 문서 수: {stats['total_documents']}")
    print(f"  법률: {stats['laws']}")
    print(f"  규칙: {stats['rules']}")
    print(f"  약관: {stats['terms']}")
    print(f"  시행령: {stats['enfor']}")
    
    # 검색 테스트
    test_query = "금융소비자보호법이란?"
    results = retriever.search(test_query)
    
    print(f"\n검색어: {test_query}")
    print(f"결과 수: {len(results)}")
    
    for i, doc in enumerate(results, 1):
        print(f"\n{i}. 유사도: {doc['similarity']:.3f} [{doc.get('table_name', 'unknown')}]")
        print(f"   내용: {doc['content'][:100]}...")
        print(f"   메타데이터: {doc['metadata']}")
    
    retriever.close()
