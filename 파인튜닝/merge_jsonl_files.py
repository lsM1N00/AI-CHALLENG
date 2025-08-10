#!/usr/bin/env python3
"""
기존 JSONL 파일들을 하나로 합치는 도구
Merge multiple JSONL files into a single file
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
            logging.FileHandler(f'merge_jsonl_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


def validate_jsonl_line(line: str, line_num: int) -> Dict[str, Any]:
    """JSONL 라인 검증 및 파싱"""
    try:
        line = line.strip()
        if not line:
            return None
        
        data = json.loads(line)
        
        # 필수 필드 확인
        if 'instruction' not in data or 'output' not in data:
            return None
        
        # input 필드가 없으면 추가
        if 'input' not in data:
            data['input'] = ""
        
        return data
        
    except json.JSONDecodeError as e:
        logging.warning(f"라인 {line_num}: JSON 파싱 오류 - {e}")
        return None
    except Exception as e:
        logging.warning(f"라인 {line_num}: 처리 오류 - {e}")
        return None


def process_jsonl_file(file_path: str, logger: logging.Logger = None) -> List[Dict[str, Any]]:
    """단일 JSONL 파일 처리"""
    if logger:
        logger.info(f"처리 중: {file_path}")
    
    valid_qa_list = []
    total_lines = 0
    valid_lines = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                qa_data = validate_jsonl_line(line, line_num)
                if qa_data:
                    valid_qa_list.append(qa_data)
                    valid_lines += 1
        
        if logger:
            logger.info(f"완료: {file_path} ({valid_lines}/{total_lines} 유효한 QA)")
        
        return valid_qa_list
        
    except Exception as e:
        if logger:
            logger.error(f"파일 처리 오류 {file_path}: {e}")
        return []


def merge_jsonl_files(input_dir: str, output_file: str, logger: logging.Logger = None) -> Dict[str, int]:
    """모든 JSONL 파일을 하나로 합치기"""
    if logger:
        logger.info(f"JSONL 파일 합치기 시작: {input_dir} -> {output_file}")
    
    # 모든 JSONL 파일 찾기
    jsonl_files = list(Path(input_dir).rglob('*.jsonl'))
    
    if not jsonl_files:
        if logger:
            logger.warning(f"'{input_dir}' 디렉토리에서 JSONL 파일을 찾을 수 없습니다.")
        return {
            'total_files': 0,
            'processed_files': 0,
            'total_qa': 0,
            'errors': 0
        }
    
    if logger:
        logger.info(f"발견된 JSONL 파일 수: {len(jsonl_files)}")
    
    stats = {
        'total_files': len(jsonl_files),
        'processed_files': 0,
        'total_qa': 0,
        'errors': 0
    }
    
    all_qa_list = []
    
    for file_path in jsonl_files:
        try:
            qa_list = process_jsonl_file(str(file_path), logger)
            if qa_list:
                all_qa_list.extend(qa_list)
                stats['processed_files'] += 1
                stats['total_qa'] += len(qa_list)
            else:
                stats['errors'] += 1
                
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
        stats['total_qa'] = len(all_qa_list)
    
    # 합쳐진 파일 저장
    if all_qa_list:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for qa in all_qa_list:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        if logger:
            logger.info(f"합치기 완료: {output_file} ({len(all_qa_list)}개 QA)")
    
    return stats


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='JSONL 파일들을 하나로 합치기')
    parser.add_argument('--input', type=str, default='./jsonl', help='입력 디렉토리 (기본값: ./jsonl)')
    parser.add_argument('--output', type=str, default='./merged_training.jsonl', help='출력 파일 (기본값: ./merged_training.jsonl)')
    
    args = parser.parse_args()
    
    # 로거 설정
    logger = setup_logging()
    logger.info("JSONL 파일 합치기 시작")
    
    try:
        stats = merge_jsonl_files(args.input, args.output, logger)
        
        logger.info("="*50)
        logger.info("합치기 완료 통계:")
        logger.info(f"총 파일 수: {stats['total_files']}")
        logger.info(f"처리된 파일 수: {stats['processed_files']}")
        logger.info(f"총 QA 수: {stats['total_qa']}")
        logger.info(f"오류 수: {stats['errors']}")
        logger.info(f"출력 파일: {args.output}")
        
    except Exception as e:
        logger.error(f"합치기 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main() 