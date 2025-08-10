#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSONL 파일의 output 형식을 <|begin_of_thought|> ... <|end_of_thought|> 형식으로 변환하는 스크립트
"""

import json
import os
from pathlib import Path

def convert_output_format(input_file_path, output_file_path=None):
    """
    JSONL 파일의 output 필드를 <|begin_of_thought|> ... <|end_of_thought|> 형식으로 변환
    
    Args:
        input_file_path (str): 입력 JSONL 파일 경로
        output_file_path (str, optional): 출력 파일 경로. None이면 자동 생성
    
    Returns:
        str: 출력 파일 경로
    """
    
    if output_file_path is None:
        # 입력 파일명에 '_converted' 추가하여 출력 파일명 생성
        input_path = Path(input_file_path)
        output_file_path = input_path.parent / f"{input_path.stem}_converted{input_path.suffix}"
    
    converted_count = 0
    error_count = 0
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile, \
             open(output_file_path, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # JSON 파싱
                    data = json.loads(line)
                    
                    # output 필드가 있는지 확인
                    if 'output' in data and data['output']:
                        # output 형식 변환
                        original_output = data['output']
                        converted_output = f"<|begin_of_thought|>{original_output}<|end_of_thought|>"
                        data['output'] = converted_output
                        converted_count += 1
                    
                    # 변환된 데이터를 새 파일에 쓰기
                    json.dump(data, outfile, ensure_ascii=False)
                    outfile.write('\n')
                    
                except json.JSONDecodeError as e:
                    print(f"라인 {line_num} JSON 파싱 오류: {e}")
                    error_count += 1
                    # 오류가 있는 라인은 그대로 복사
                    outfile.write(line + '\n')
                except Exception as e:
                    print(f"라인 {line_num} 처리 오류: {e}")
                    error_count += 1
                    # 오류가 있는 라인은 그대로 복사
                    outfile.write(line + '\n')
        
        print(f"변환 완료!")
        print(f"입력 파일: {input_file_path}")
        print(f"출력 파일: {output_file_path}")
        print(f"변환된 라인 수: {converted_count}")
        print(f"오류 발생 라인 수: {error_count}")
        
        return str(output_file_path)
        
    except FileNotFoundError:
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_file_path}")
        return None
    except Exception as e:
        print(f"오류: {e}")
        return None

def preview_conversion(input_file_path, num_lines=5):
    """
    변환 결과를 미리보기
    
    Args:
        input_file_path (str): 입력 JSONL 파일 경로
        num_lines (int): 미리보기할 라인 수
    """
    print(f"변환 미리보기 (처음 {num_lines}개 라인):")
    print("-" * 50)
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            for i, line in enumerate(infile):
                if i >= num_lines:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    if 'output' in data:
                        print(f"라인 {i+1}:")
                        print(f"  원본 output: {data['output'][:100]}...")
                        converted = f"<|begin_of_thought|>{data['output']}<|end_of_thought|>"
                        print(f"  변환된 output: {converted[:100]}...")
                        print()
                except:
                    continue
                    
    except Exception as e:
        print(f"미리보기 오류: {e}")

def main():
    """메인 함수"""
    print("JSONL 파일 output 형식 변환 도구")
    print("=" * 50)
    
    # 사용자로부터 파일 경로 입력 받기
    while True:
        file_path = input("\n변환할 JSONL 파일의 전체 경로를 입력하세요: ").strip()
        
        # 따옴표 제거
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        elif file_path.startswith("'") and file_path.endswith("'"):
            file_path = file_path[1:-1]
        
        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            print(f"오류: 파일을 찾을 수 없습니다: {file_path}")
            retry = input("다시 시도하시겠습니까? (y/n): ").lower()
            if retry not in ['y', 'yes', '예']:
                return
            continue
        
        # JSONL 파일인지 확인
        if not file_path.lower().endswith('.jsonl'):
            print("경고: .jsonl 확장자가 아닙니다. 계속 진행하시겠습니까? (y/n): ").lower()
            if retry not in ['y', 'yes', '예']:
                continue
        
        break
    
    selected_file = Path(file_path)
    print(f"\n선택된 파일: {selected_file.name}")
    print(f"파일 경로: {selected_file.absolute()}")
    
    # 미리보기
    preview_conversion(selected_file)
    
    # 변환 실행 여부 확인
    confirm = input("\n변환을 진행하시겠습니까? (y/n): ").lower()
    if confirm in ['y', 'yes', '예']:
        output_file = convert_output_format(selected_file)
        if output_file:
            print(f"\n변환된 파일이 저장되었습니다: {output_file}")
    else:
        print("변환이 취소되었습니다.")

if __name__ == "__main__":
    main() 