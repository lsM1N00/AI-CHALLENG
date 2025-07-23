

import psycopg2
import sys

# --- 팀원 접속 정보 ---
# host: 데이터베이스 서버가 실행 중인 컴퓨터의 IP 주소
#       (이 주소는 같은 네트워크에 있을 때만 유효합니다)
# dbname: 접속할 데이터베이스 이름
# user: 접속에 사용할 사용자 이름
# password: 해당 사용자의 비밀번호
# port: PostgreSQL 기본 포트
conn_info = {
    "host": "192.0.0.2",
    "dbname": "financedb",
    "user": "teammate",
    "password": "0717",
    "port": 5432
}

conn = None
try:
    # 데이터베이스에 연결
    print(f"데이터베이스 서버({conn_info['host']})에 연결을 시도합니다...")
    conn = psycopg2.connect(**conn_info)

    # 커서(cursor)를 가져와서 쿼리 실행
    cur = conn.cursor()
    cur.execute("SELECT version();")

    # 결과 가져오기
    db_version = cur.fetchone()
    print("\n--- 연결 성공 ---")
    print(f"PostgreSQL 데이터베이스 버전: {db_version[0]}")
    print("-----------------")

    # 커서 닫기
    cur.close()

except psycopg2.OperationalError as e:
    print("\n--- 연결 실패 ---", file=sys.stderr)
    print(f"오류: {e}", file=sys.stderr)
    print("\n[문제 해결 가이드]", file=sys.stderr)
    print("1. 서버 IP 주소(192.0.0.2)가 정확한지, 서버 컴퓨터가 켜져 있는지 확인하세요.", file=sys.stderr)
    print("2. 서버 컴퓨터의 방화벽이 5432 포트 연결을 허용하는지 확인하세요.", file=sys.stderr)
    print("3. 접속 정보(DB이름, 사용자, 비밀번호)가 정확한지 확인하세요.", file=sys.stderr)
    print("4. psycopg2 라이브러리가 설치되어 있는지 확인하세요. (pip install psycopg2-binary)", file=sys.stderr)
    print("-----------------", file=sys.stderr)

except Exception as e:
    print(f"예상치 못한 오류가 발생했습니다: {e}", file=sys.stderr)

finally:
    if conn is not None:
        # 연결 닫기
        conn.close()
        print("\n데이터베이스 연결을 닫았습니다.")
