-- 법령 및 규정 테이블 생성 스크립트
-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- laws 테이블 (법령)
CREATE TABLE IF NOT EXISTS laws (
    id SERIAL PRIMARY KEY,
    jang VARCHAR(100),           -- 장
    joo VARCHAR(100),            -- 조
    hang VARCHAR(100),           -- 항
    num INTEGER,                 -- 번호
    context TEXT,                -- 내용
    vector vector(1536),         -- 임베딩 벡터 (OpenAI 기준)
    metadata JSONB               -- 메타데이터
);

-- enfor 테이블 (시행령)
CREATE TABLE IF NOT EXISTS enfor (
    id SERIAL PRIMARY KEY,
    jang VARCHAR(100),           -- 장
    joo VARCHAR(100),            -- 조
    hang VARCHAR(100),           -- 항
    num INTEGER,                 -- 번호
    context TEXT,                -- 내용
    vector vector(1536),         -- 임베딩 벡터
    metadata JSONB               -- 메타데이터
);

-- terms 테이블 (용어)
CREATE TABLE IF NOT EXISTS terms (
    id SERIAL PRIMARY KEY,
    jang VARCHAR(100),           -- 장
    joo VARCHAR(100),            -- 조
    hang VARCHAR(100),           -- 항
    num INTEGER,                 -- 번호
    context TEXT,                -- 내용
    vector vector(1536),         -- 임베딩 벡터
    metadata JSONB               -- 메타데이터
);

-- rule 테이블 (규칙)
CREATE TABLE IF NOT EXISTS rule (
    id SERIAL PRIMARY KEY,
    jang VARCHAR(100),           -- 장
    joo VARCHAR(100),            -- 조
    hang VARCHAR(100),           -- 항
    num INTEGER,                 -- 번호
    context TEXT,                -- 내용
    vector vector(1536),         -- 임베딩 벡터
    metadata JSONB               -- 메타데이터
);

-- 인덱스 생성 (검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_laws_vector ON laws USING ivfflat (vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_enfor_vector ON enfor USING ivfflat (vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_terms_vector ON terms USING ivfflat (vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_rule_vector ON rule USING ivfflat (vector vector_cosine_ops);

-- 메타데이터 인덱스
CREATE INDEX IF NOT EXISTS idx_laws_metadata ON laws USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_enfor_metadata ON enfor USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_terms_metadata ON terms USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_rule_metadata ON rule USING gin (metadata);

-- 테이블 생성 확인
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_name IN ('laws', 'enfor', 'terms', 'rule')
ORDER BY table_name, ordinal_position; 