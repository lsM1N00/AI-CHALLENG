# JSON to JSONL 변환 도구

법률 QA 데이터를 JSON 형식에서 JSONL 형식으로 변환하는 도구입니다.

## 기능

- **단일 파일 변환**: 개별 JSON 파일을 JSONL로 변환
- **배치 변환**: 디렉토리 내 모든 JSON 파일을 일괄 변환
- **두 가지 모드**: 
  - `simple`: 기본 변환 (1:1 매핑)
  - `advanced`: 고급 변환 (1개 입력에서 여러 QA 생성)
- **자동 파일 타입 감지**: JSON 객체 또는 배열 자동 감지
- **로깅**: 상세한 처리 과정 로그 제공
- **합치기 기능**: 모든 JSON을 하나의 JSONL 파일로 합치기
- **input 필드**: 기본적으로 비어있는 input 필드 포함

## 설치 및 사용

### 0. 빠른 시작
```bash
# 1. json 폴더에 JSON 파일들을 넣기
mkdir json
# (JSON 파일들을 json 폴더에 복사)

# 2. 변환 실행
python convert_all.py
```

### 1. 기본 사용법

#### 간단한 실행 (권장)
```bash
# json 폴더의 모든 파일을 변환
python convert_all.py
```

#### 명령줄 직접 실행
```bash
# 단일 파일 변환 (간단한 모드)
python json_to_jsonl_converter.py --input data.json --output output.jsonl --mode simple

# 단일 파일 변환 (고급 모드)
python json_to_jsonl_converter.py --input data.json --output output.jsonl --mode advanced

# 디렉토리 전체 변환 (기본값 사용)
python json_to_jsonl_converter.py --input ./json --output ./jsonl --mode simple

# 디렉토리 전체 변환 (사용자 지정)
python json_to_jsonl_converter.py --input ./json_files/ --output ./jsonl_files/ --mode advanced

# 모든 JSON을 하나의 파일로 합치기
python json_to_jsonl_converter.py --input ./json/ --output ./jsonl/ --mode simple --merge

# 기존 JSONL 파일들을 하나로 합치기
python json_to_jsonl_converter.py --input ./jsonl/ --output ./merged_training.jsonl --merge-jsonl
```

### 2. 매개변수 설명

- `--input`: 입력 파일 또는 디렉토리 경로
- `--output`: 출력 파일 또는 디렉토리 경로
- `--mode`: 변환 모드 (`simple` 또는 `advanced`)

## 변환 모드

### Simple 모드
기본적인 1:1 변환을 수행합니다.

**입력 JSON 형식:**
```json
{
  "taskinfo": {
    "input": "질문",
    "output": "답변"
  }
}
```

**출력 JSONL 형식:**
```json
{"instruction": "질문", "input": "", "output": "답변"}
```

### Advanced 모드
하나의 입력에서 여러 QA를 생성합니다.

**입력 JSON 형식:**
```json
{
  "taskinfo": {
    "input": "질문",
    "output": "답변",
    "sentences": ["문장1", "문장2", "문장3"]
  },
  "info": {
    "casenames": "사건명"
  }
}
```

**출력 JSONL 형식 (여러 QA):**
```json
{"instruction": "질문", "input": "", "output": "답변"}
{"instruction": "다음 판결문을 바탕으로 질문에 답하세요.", "input": "판결문: 핵심 문장들...\n\n질문: 질문", "output": "답변"}
{"instruction": "사건명 사건에서 법원의 판단은?", "input": "", "output": "답변"}
```

## 핵심 기능

### 1. 핵심 문장 추출
판결문에서 중요한 문장만 추출하여 컨텍스트로 활용합니다.

**추출 패턴:**
- "주의의무", "판결", "따라서", "그러므로"
- "인정", "책임", "법원", "판단", "결론", "이유"

### 2. 자동 파일 타입 감지
- **JSON 객체**: 단일 객체 파일
- **JSON 배열**: 여러 객체가 배열로 구성된 파일

### 3. 오류 처리
- 파일 읽기/쓰기 오류 처리
- 잘못된 JSON 형식 처리
- 누락된 필드 처리

## 사용 예시

### 예시 1: 단일 파일 변환
```bash
python json_to_jsonl_converter.py \
  --input legal_qa.json \
  --output legal_qa_training.jsonl \
  --mode advanced
```

### 예시 2: 디렉토리 배치 변환
```bash
python json_to_jsonl_converter.py \
  --input ./legal_data/ \
  --output ./training_data/ \
  --mode simple
```

## 출력 파일

변환 후 생성되는 파일들:
- `*.jsonl`: JSONL 형식의 학습 데이터
- `converter_YYYYMMDD_HHMMSS.log`: 처리 로그

## 로그 정보

변환 과정에서 다음 정보를 로그로 기록합니다:
- 처리된 파일 수
- 생성된 QA 수
- 오류 발생 파일
- 처리 시간

## 주의사항

1. **입력 파일 형식**: `taskinfo.input`과 `taskinfo.output` 필드가 필요합니다.
2. **Advanced 모드**: `sentences` 필드가 있으면 더 풍부한 QA를 생성합니다.
3. **파일 인코딩**: UTF-8 인코딩을 사용합니다.
4. **대용량 파일**: 메모리 효율적으로 처리됩니다.

## 예시 실행

```bash
# 예시 스크립트 실행
python convert_example.py
```

이 스크립트는 다양한 변환 예시를 보여줍니다.

## 라이선스

이 도구는 교육 및 연구 목적으로 자유롭게 사용할 수 있습니다. 