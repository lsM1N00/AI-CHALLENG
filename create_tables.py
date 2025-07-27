"""
테이블 생성 스크립트 - laws, enfor, terms, rule 테이블 생성
"""
import psycopg2
import config

def create_tables():
    """테이블 생성 함수"""
    conn = None
    try:
        # 데이터베이스 연결
        conn = psycopg2.connect(
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        
        cursor = conn.cursor()
        
        # SQL 스크립트 읽기
        with open('ai-/create_tables.sql', 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # SQL 실행
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ 테이블 생성 완료!")
        print("생성된 테이블:")
        print("- laws (법령)")
        print("- enfor (시행령)")
        print("- terms (용어)")
        print("- rule (규칙)")
        
        # 테이블 구조 확인
        cursor.execute("""
            SELECT 
                table_name,
                column_name,
                data_type
            FROM information_schema.columns 
            WHERE table_name IN ('laws', 'enfor', 'terms', 'rule')
            ORDER BY table_name, ordinal_position;
        """)
        
        results = cursor.fetchall()
        print("\n📋 테이블 구조:")
        current_table = None
        for row in results:
            table_name, column_name, data_type = row
            if table_name != current_table:
                print(f"\n{table_name.upper()} 테이블:")
                current_table = table_name
            print(f"  - {column_name}: {data_type}")
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_tables() 