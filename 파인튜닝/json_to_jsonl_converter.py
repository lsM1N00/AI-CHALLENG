#!/usr/bin/env python3
"""
JSON을 JSONL 형식으로 변환하는 도구
JSON to JSONL Converter Tool
"""

import json
import argparse
import os
import sys
from typing import List, Dict, Any
from pathlib import Path


class JSONToJSONLConverter:
    """JSON을 JSONL 형식으로 변환하는 클래스"""
    
    def __init__(self):
        self.converted_count = 0
        self.error_count = 0
    
    def convert_json_to_jsonl(self, input_file: str, output_file: str = None) -> bool:
        """
        JSON 파일을 JSONL 형식으로 변환
        
        Args:
            input_file: 입력 JSON 파일 경로
            output_file: 출력 JSONL 파일 경로 (None이면 자동 생성)
        
        Returns:
            변환 성공 여부
        """
        try:
            # 입력 파일 확인
            if not os.path.exists(input_file):
                print(f"❌ 입력 파일을 찾을 수 없습니다: {input_file}")
                return False
            
            # 출력 파일명 자동 생성
            if output_file is None:
                input_path = Path(input_file)
                output_file = input_path.parent / f"{input_path.stem}.jsonl"
            
            print(f"📁 입력 파일: {input_file}")
            print(f"📁 출력 파일: {output_file}")
            
            # JSON 파일 읽기
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # qa_pairs 추출
            qa_pairs = data.get('qa_pairs', [])
            if not qa_pairs:
                print("❌ qa_pairs가 없거나 비어있습니다.")
                return False
            
            print(f"📊 발견된 QA 쌍: {len(qa_pairs)}개")
            
            # JSONL 형식으로 변환
            converted_lines = []
            for qa_pair in qa_pairs:
                jsonl_item = self._convert_qa_pair_to_jsonl(qa_pair)
                if jsonl_item:
                    converted_lines.append(jsonl_item)
                    self.converted_count += 1
                else:
                    self.error_count += 1
            
            # JSONL 파일 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in converted_lines:
                    f.write(json.dumps(line, ensure_ascii=False) + '\n')
            
            print(f"✅ 변환 완료!")
            print(f"   - 성공: {self.converted_count}개")
            print(f"   - 실패: {self.error_count}개")
            print(f"   - 출력 파일: {output_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ 변환 중 오류 발생: {e}")
            return False
    
    def _convert_qa_pair_to_jsonl(self, qa_pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        QA 쌍을 JSONL 형식으로 변환
        
        Args:
            qa_pair: QA 쌍 데이터
        
        Returns:
            JSONL 형식의 데이터
        """
        try:
            # 필수 필드 확인
            question = qa_pair.get('question', '')
            answer = qa_pair.get('answer', '')
            
            if not question or not answer:
                print(f"⚠️ 필수 필드 누락: question={bool(question)}, answer={bool(answer)}")
                return None
            
            # JSONL 형식으로 변환
            jsonl_item = {
                "instruction": question,
                "input": "",  # input은 비워둠
                "output": answer
            }
            
            return jsonl_item
            
        except Exception as e:
            print(f"⚠️ QA 쌍 변환 실패: {e}")
            return None
    
    def convert_directory(self, input_dir: str, output_dir: str = None) -> bool:
        """
        디렉토리 내의 모든 JSON 파일을 JSONL로 변환
        
        Args:
            input_dir: 입력 디렉토리
            output_dir: 출력 디렉토리 (None이면 입력 디렉토리와 동일)
        
        Returns:
            변환 성공 여부
        """
        try:
            if not os.path.exists(input_dir):
                print(f"❌ 입력 디렉토리를 찾을 수 없습니다: {input_dir}")
                return False
            
            # 출력 디렉토리 생성
            if output_dir is None:
                output_dir = input_dir
            os.makedirs(output_dir, exist_ok=True)
            
            # JSON 파일 찾기
            json_files = []
            for file in os.listdir(input_dir):
                if file.lower().endswith('.json'):
                    json_files.append(os.path.join(input_dir, file))
            
            if not json_files:
                print(f"❌ {input_dir}에서 JSON 파일을 찾을 수 없습니다.")
                return False
            
            print(f"📁 발견된 JSON 파일: {len(json_files)}개")
            
            # 각 파일 변환
            success_count = 0
            for json_file in json_files:
                print(f"\n🔄 변환 중: {os.path.basename(json_file)}")
                
                # 출력 파일명 생성
                input_path = Path(json_file)
                output_file = os.path.join(output_dir, f"{input_path.stem}.jsonl")
                
                if self.convert_json_to_jsonl(json_file, output_file):
                    success_count += 1
                else:
                    print(f"❌ 변환 실패: {json_file}")
            
            print(f"\n📊 전체 변환 완료!")
            print(f"   - 성공: {success_count}/{len(json_files)}개")
            
            return success_count == len(json_files)
            
        except Exception as e:
            print(f"❌ 디렉토리 변환 중 오류 발생: {e}")
            return False


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='JSON 파일을 JSONL 형식으로 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 단일 파일 변환
  python json_to_jsonl_converter.py --input data.json --output data.jsonl
  
  # 자동 출력 파일명으로 변환
  python json_to_jsonl_converter.py --input data.json
  
  # 디렉토리 내 모든 JSON 파일 변환
  python json_to_jsonl_converter.py --input-dir ./json_files --output-dir ./jsonl_files
  
  # 현재 디렉토리의 모든 JSON 파일 변환
  python json_to_jsonl_converter.py --input-dir .
        """
    )
    
    # 입력 옵션 (파일 또는 디렉토리)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input', type=str, help='입력 JSON 파일')
    input_group.add_argument('--input-dir', type=str, help='입력 디렉토리 (모든 JSON 파일 변환)')
    
    # 출력 옵션
    parser.add_argument('--output', type=str, help='출력 JSONL 파일 (단일 파일 변환 시)')
    parser.add_argument('--output-dir', type=str, help='출력 디렉토리 (디렉토리 변환 시)')
    
    args = parser.parse_args()
    
    converter = JSONToJSONLConverter()
    
    try:
        if args.input:
            # 단일 파일 변환
            success = converter.convert_json_to_jsonl(args.input, args.output)
        elif args.input_dir:
            # 디렉토리 변환
            success = converter.convert_directory(args.input_dir, args.output_dir)
        else:
            print("❌ 입력 파일 또는 디렉토리를 지정해야 합니다.")
            return 1
        
        if success:
            print("\n🎉 변환이 성공적으로 완료되었습니다!")
            return 0
        else:
            print("\n❌ 변환 중 오류가 발생했습니다.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 