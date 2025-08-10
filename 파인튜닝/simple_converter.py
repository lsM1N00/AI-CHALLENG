#!/usr/bin/env python3
"""
단순한 JSON을 JSONL로 변환하는 도구
Simple JSON to JSONL Converter
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'simple_converter_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


def convert_simple_format(data: Dict[str, Any]) -> Dict[str, str]:
    """단순한 형식으로 변환"""
    # 다양한 JSON 구조 지원
    instruction = ""
    output = ""
    
    # taskinfo 구조 확인
    if 'taskinfo' in data:
        taskinfo = data['taskinfo']
        instruction = taskinfo.get('input', '')
        output = taskinfo.get('output', '')
    # 직접 구조 확인
    elif 'input' in data and 'output' in data:
        instruction = data.get('input', '')
        output = data.get('output', '')
    # 다른 가능한 구조들
    elif 'question' in data and 'answer' in data:
        instruction = data.get('question', '')
        output = data.get('answer', '')
    elif 'instruction' in data and 'output' in data:
        instruction = data.get('instruction', '')
        output = data.get('output', '')
    # label 구조 확인
    elif 'label' in data:
        label = data['label']
        instruction = label.get('input', '')
        output = label.get('output', '')
    else:
        # 구조를 로그로 출력하여 디버깅
        print(f"알 수 없는 JSON 구조: {list(data.keys())}")
        return None
    
    return {
        "instruction": instruction,
        "input": "",
        "output": output
    }


def process_json_file(file_path: str, output_path: str, logger: logging.Logger = None) -> int:
    """단일 JSON 파일을 JSONL로 변환"""
    if logger:
        logger.info(f"처리 중: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 단순한 형식으로 변환
        simple_format = convert_simple_format(data)
        
        if simple_format is None:
            if logger:
                logger.warning(f"변환 실패: {file_path}")
            return 0
        
        # JSONL 파일에 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(simple_format, ensure_ascii=False) + '\n')
        
        if logger:
            logger.info(f"변환 완료: {output_path}")
        
        return 1
        
    except Exception as e:
        if logger:
            logger.error(f"파일 처리 오류 {file_path}: {e}")
        return 0


def process_json_array_file(file_path: str, output_path: str, logger: logging.Logger = None) -> int:
    """JSON 배열 파일을 JSONL로 변환"""
    if logger:
        logger.info(f"배열 파일 처리 중: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
        
        total_qa = 0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for data in data_list:
                simple_format = convert_simple_format(data)
                if simple_format is not None:
                    f.write(json.dumps(simple_format, ensure_ascii=False) + '\n')
                    total_qa += 1
        
        if logger:
            logger.info(f"배열 변환 완료: {total_qa}개 QA 생성")
        
        return total_qa
        
    except Exception as e:
        if logger:
            logger.error(f"배열 파일 처리 오류 {file_path}: {e}")
        return 0


def detect_file_type(file_path: str) -> str:
    """파일 타입 감지 (단일 객체 또는 배열)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return 'array'
        else:
            return 'object'
    except Exception:
        return 'unknown'


def convert_directory(input_dir: str, output_dir: str, logger: logging.Logger = None) -> Dict[str, int]:
    """디렉토리 내 모든 JSON 파일을 JSONL로 변환"""
    if logger:
        logger.info(f"디렉토리 변환 시작: {input_dir} -> {output_dir}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    stats = {
        'total_files': 0,
        'processed_files': 0,
        'total_qa': 0,
        'errors': 0
    }
    
    # 모든 JSON 파일 찾기 (하위 디렉토리 포함)
    json_files = list(Path(input_dir).rglob('*.json'))
    
    if not json_files:
        if logger:
            logger.warning(f"'{input_dir}' 디렉토리에서 JSON 파일을 찾을 수 없습니다.")
        return stats
    
    if logger:
        logger.info(f"발견된 JSON 파일 수: {len(json_files)}")
    
    # 하나의 파일에 모든 QA 저장
    merged_output_path = Path(output_dir) / "training_min_.jsonl"
    all_qa_list = []
    
    # 기존 training_min_.jsonl 파일이 있으면 로드
    existing_qa_count = 0
    if merged_output_path.exists():
        try:
            with open(merged_output_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            existing_qa = json.loads(line)
                            all_qa_list.append(existing_qa)
                            existing_qa_count += 1
                        except json.JSONDecodeError:
                            continue
            
            if logger:
                logger.info(f"기존 파일 로드: {existing_qa_count}개 QA")
        except Exception as e:
            if logger:
                logger.warning(f"기존 파일 로드 실패: {e}")
    
    # 새로운 QA 추가
    new_qa_count = 0
    for file_path in json_files:
        stats['total_files'] += 1
        
        try:
            if logger:
                logger.info(f"처리 중: {file_path.name}")
            
            file_type = detect_file_type(str(file_path))
            
            if file_type == 'array':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
                
                for data in data_list:
                    simple_format = convert_simple_format(data)
                    if simple_format is not None:
                        all_qa_list.append(simple_format)
                        new_qa_count += 1
                    
            elif file_type == 'object':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                simple_format = convert_simple_format(data)
                if simple_format is not None:
                    all_qa_list.append(simple_format)
                    new_qa_count += 1
                
            else:
                if logger:
                    logger.warning(f"알 수 없는 파일 형식: {file_path}")
                stats['errors'] += 1
                continue
            
            stats['processed_files'] += 1
            
        except Exception as e:
            if logger:
                logger.error(f"파일 처리 실패 {file_path}: {e}")
            stats['errors'] += 1
    
    # 중복 제거 (instruction 기반)
    if all_qa_list:
        unique_qa = []
        seen_instructions = set()
        
        for qa in all_qa_list:
            instruction = qa.get('instruction', '').strip()
            if instruction and instruction not in seen_instructions:
                seen_instructions.add(instruction)
                unique_qa.append(qa)
        
        if logger:
            logger.info(f"중복 제거: {len(all_qa_list)} -> {len(unique_qa)} QA")
        
        all_qa_list = unique_qa
    
    # 모든 QA를 하나의 파일에 저장
    if all_qa_list:
        with open(merged_output_path, 'w', encoding='utf-8') as f:
            for qa in all_qa_list:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        stats['total_qa'] = len(all_qa_list)
        if logger:
            logger.info(f"합치기 완료: {merged_output_path}")
            logger.info(f"기존 QA: {existing_qa_count}개, 새로 추가된 QA: {new_qa_count}개")
            logger.info(f"총 QA: {len(all_qa_list)}개")
    
    return stats


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='단순한 JSON을 JSONL 형식으로 변환')
    parser.add_argument('--input', type=str, default='./json', help='입력 파일 또는 디렉토리 (기본값: ./json)')
    parser.add_argument('--output', type=str, default='./jsonl', help='출력 파일 또는 디렉토리 (기본값: ./jsonl)')
    
    args = parser.parse_args()
    
    # 로거 설정
    logger = setup_logging()
    logger.info("단순한 JSON to JSONL 변환 시작")
    
    try:
        if os.path.isdir(args.input):
            # 디렉토리 처리
            stats = convert_directory(args.input, args.output, logger)
            
            if stats:
                logger.info("="*50)
                logger.info("변환 완료 통계:")
                logger.info(f"총 파일 수: {stats['total_files']}")
                logger.info(f"처리된 파일 수: {stats['processed_files']}")
                logger.info(f"총 QA 수: {stats['total_qa']}")
                logger.info(f"오류 수: {stats['errors']}")
                logger.info(f"합쳐진 파일: {os.path.join(args.output, 'training_min_.jsonl')}")
                logger.info("기존 파일과 새로운 데이터가 합쳐졌습니다.")
            else:
                logger.error("변환 중 오류가 발생했습니다.")
            
        else:
            # 단일 파일 처리
            file_type = detect_file_type(args.input)
            
            if file_type == 'array':
                qa_count = process_json_array_file(args.input, args.output, logger)
            elif file_type == 'object':
                qa_count = process_json_file(args.input, args.output, logger)
            else:
                logger.error(f"알 수 없는 파일 형식: {args.input}")
                return
            
            logger.info(f"변환 완료: {qa_count}개 QA 생성")
            
    except Exception as e:
        logger.error(f"변환 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main() 