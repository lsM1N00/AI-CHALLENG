import json

input_file = "/Users/sangmin/Desktop/ai agent/파인튜닝/output/training_dataset.jsonl"   # 기존 파일
output_file = "KoAplaca_training_dataset.jsonl"  # 새로 저장할 파일

line_count = 0
error_count = 0

with open(input_file, 'r', encoding='utf-8') as fin, open(output_file, 'w', encoding='utf-8') as fout:
    for line_num, line in enumerate(fin, 1):
        line = line.strip()
        
        # 빈 줄 건너뛰기
        if not line:
            continue
            
        try:
            data = json.loads(line)
            
            # "input" 내용을 "instruction"에 넣고, input은 공란으로
            new_data = {
                "instruction": data.get("input", ""),  # input이 없으면 빈 문자열 처리
                "input": "",
                "output": data.get("output", "")
            }

            fout.write(json.dumps(new_data, ensure_ascii=False) + "\n")
            line_count += 1
            
        except json.JSONDecodeError as e:
            error_count += 1
            print(f"❌ JSON 파싱 오류 (라인 {line_num}): {e}")
            print(f"   문제가 된 라인: {line[:100]}...")
            continue
        except Exception as e:
            error_count += 1
            print(f"❌ 기타 오류 (라인 {line_num}): {e}")
            continue

print(f"✅ 변환 완료!")
print(f"📊 처리된 라인: {line_count}개")
print(f"❌ 오류 발생: {error_count}개")
