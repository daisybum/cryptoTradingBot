#!/usr/bin/env python3
"""
민감한 정보 감지 스크립트

이 스크립트는 프로젝트 내의 파일에서 API 키, 토큰, 비밀번호 등 
하드코딩된 민감한 정보를 감지합니다.
"""

import os
import re
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 민감한 정보 패턴
SENSITIVE_PATTERNS = [
    # API 키 패턴
    r'(?i)(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']',
    r'(?i)(access[_-]?key|accesskey)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']',
    
    # 토큰 패턴
    r'(?i)(token|auth[_-]?token)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']',
    r'(?i)(jwt|bearer)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']',
    
    # 비밀번호 패턴
    r'(?i)(password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\'\s]{8,})["\']',
    r'(?i)(secret|secret[_-]?key)["\']?\s*[:=]\s*["\']([^"\'\s]{8,})["\']',
    
    # 기타 민감한 정보
    r'(?i)(private[_-]?key)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']',
    r'(?i)(credential)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']',
]

# 기본 제외 디렉토리 및 파일
DEFAULT_EXCLUDES = [
    '.git',
    '.github',
    'venv',
    'env',
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.DS_Store',
    'node_modules',
    '.idea',
    '.vscode',
    'project.env',  # project.env 파일은 민감한 정보를 저장하는 곳이므로 제외
    'config/env/project.env',
    '*.log',
    '*.bak',
    '*.swp',
    '*.swo',
]

# 허용 목록 (무시할 패턴)
ALLOWLIST = [
    r'example\.com',
    r'dummy',
    r'placeholder',
    r'your_',
    r'YOUR_',
    r'example',
    r'test',
    r'sample',
]

class SecretDetector:
    """민감한 정보 감지 클래스"""
    
    def __init__(
        self,
        project_root: Path,
        exclude_dirs: List[str] = None,
        exclude_files: List[str] = None,
        exclude_patterns: List[str] = None,
        min_entropy: float = 3.5,
        output_file: Optional[str] = None,
        verbose: bool = False
    ):
        """
        민감한 정보 감지기 초기화
        
        Args:
            project_root: 프로젝트 루트 디렉토리
            exclude_dirs: 제외할 디렉토리 목록
            exclude_files: 제외할 파일 목록
            exclude_patterns: 제외할 패턴 목록
            min_entropy: 최소 엔트로피 값 (낮을수록 더 많은 결과 포함)
            output_file: 결과를 저장할 파일 경로
            verbose: 상세 로깅 여부
        """
        self.project_root = project_root
        self.exclude_dirs = exclude_dirs or []
        self.exclude_files = exclude_files or []
        self.exclude_patterns = exclude_patterns or []
        self.min_entropy = min_entropy
        self.output_file = output_file
        self.verbose = verbose
        
        # 결과 저장소
        self.findings = []
        
        # 컴파일된 정규식 패턴
        self.compiled_patterns = [re.compile(pattern) for pattern in SENSITIVE_PATTERNS]
        self.compiled_allowlist = [re.compile(pattern) for pattern in ALLOWLIST]
        
        # 로깅 레벨 설정
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        logger.debug(f"프로젝트 루트: {project_root}")
        logger.debug(f"제외 디렉토리: {self.exclude_dirs}")
        logger.debug(f"제외 파일: {self.exclude_files}")
    
    def is_excluded(self, path: Path) -> bool:
        """
        파일이나 디렉토리가 제외 목록에 있는지 확인
        
        Args:
            path: 확인할 경로
            
        Returns:
            bool: 제외 목록에 있으면 True, 없으면 False
        """
        # 상대 경로 가져오기
        rel_path = path.relative_to(self.project_root)
        
        # 디렉토리 제외 확인
        for exclude_dir in self.exclude_dirs:
            if any(part == exclude_dir for part in rel_path.parts):
                return True
        
        # 파일 제외 확인
        if path.is_file():
            # 파일 이름 기반 제외
            for exclude_file in self.exclude_files:
                if path.name == exclude_file or path.match(exclude_file):
                    return True
            
            # 패턴 기반 제외
            for exclude_pattern in self.exclude_patterns:
                if re.search(exclude_pattern, str(rel_path)):
                    return True
        
        return False
    
    def calculate_entropy(self, string: str) -> float:
        """
        문자열의 엔트로피 계산 (Shannon 엔트로피)
        
        Args:
            string: 엔트로피를 계산할 문자열
            
        Returns:
            float: 엔트로피 값
        """
        import math
        
        # 빈 문자열이면 0 반환
        if not string:
            return 0
        
        # 문자 빈도 계산
        char_count = {}
        for char in string:
            char_count[char] = char_count.get(char, 0) + 1
        
        # 엔트로피 계산
        entropy = 0
        for count in char_count.values():
            freq = count / len(string)
            entropy -= freq * math.log2(freq)
        
        return entropy
    
    def is_allowlisted(self, value: str) -> bool:
        """
        값이 허용 목록에 있는지 확인
        
        Args:
            value: 확인할 값
            
        Returns:
            bool: 허용 목록에 있으면 True, 없으면 False
        """
        for pattern in self.compiled_allowlist:
            if pattern.search(value):
                return True
        return False
    
    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        파일에서 민감한 정보 스캔
        
        Args:
            file_path: 스캔할 파일 경로
            
        Returns:
            List[Dict[str, Any]]: 발견된 민감한 정보 목록
        """
        findings = []
        
        # 이진 파일이나 큰 파일은 건너뛰기
        if self.is_binary_file(file_path) or file_path.stat().st_size > 1024 * 1024 * 10:  # 10MB 이상
            logger.debug(f"건너뛰기: {file_path} (이진 파일 또는 큰 파일)")
            return findings
        
        try:
            # 파일 내용 읽기
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 각 줄 처리
            for i, line in enumerate(content.splitlines(), 1):
                for pattern in self.compiled_patterns:
                    matches = pattern.finditer(line)
                    for match in matches:
                        # 키와 값 추출
                        key = match.group(1)
                        value = match.group(2)
                        
                        # 허용 목록에 있는지 확인
                        if self.is_allowlisted(value):
                            continue
                        
                        # 엔트로피 계산
                        entropy = self.calculate_entropy(value)
                        
                        # 엔트로피가 낮으면 건너뛰기
                        if entropy < self.min_entropy:
                            continue
                        
                        # 발견 정보 추가
                        findings.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': i,
                            'key': key,
                            'value': value,
                            'entropy': entropy,
                            'line_content': line.strip()
                        })
            
        except Exception as e:
            logger.error(f"파일 스캔 중 오류 발생: {file_path}, {e}")
        
        return findings
    
    def is_binary_file(self, file_path: Path) -> bool:
        """
        파일이 이진 파일인지 확인
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            bool: 이진 파일이면 True, 아니면 False
        """
        # 파일 확장자로 확인
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.pdf', '.zip',
            '.tar', '.gz', '.tgz', '.rar', '.7z', '.exe', '.dll', '.so', '.dylib',
            '.pyc', '.pyo', '.pyd', '.db', '.sqlite', '.sqlite3', '.bin'
        }
        
        if file_path.suffix.lower() in binary_extensions:
            return True
        
        # 파일 내용으로 확인 (처음 1024바이트만)
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk  # NULL 바이트가 있으면 이진 파일로 간주
        except Exception:
            return True  # 오류 발생 시 이진 파일로 간주
    
    def scan_directory(self, directory: Path = None) -> None:
        """
        디렉토리 스캔
        
        Args:
            directory: 스캔할 디렉토리 (기본값: 프로젝트 루트)
        """
        directory = directory or self.project_root
        
        logger.info(f"디렉토리 스캔 중: {directory}")
        
        for item in directory.iterdir():
            # 제외 목록에 있는지 확인
            if self.is_excluded(item):
                logger.debug(f"제외됨: {item}")
                continue
            
            # 디렉토리면 재귀 호출
            if item.is_dir():
                self.scan_directory(item)
            
            # 파일이면 스캔
            elif item.is_file():
                logger.debug(f"파일 스캔 중: {item}")
                findings = self.scan_file(item)
                if findings:
                    self.findings.extend(findings)
    
    def run(self) -> List[Dict[str, Any]]:
        """
        스캔 실행
        
        Returns:
            List[Dict[str, Any]]: 발견된 민감한 정보 목록
        """
        logger.info("민감한 정보 스캔 시작...")
        
        # 디렉토리 스캔
        self.scan_directory()
        
        # 결과 정렬 (파일 이름, 줄 번호 순)
        self.findings.sort(key=lambda x: (x['file'], x['line']))
        
        # 결과 출력
        if self.findings:
            logger.info(f"발견된 민감한 정보: {len(self.findings)}개")
            
            # 결과 파일에 저장
            if self.output_file:
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'project_root': str(self.project_root),
                        'findings': self.findings
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"결과가 {self.output_file}에 저장되었습니다.")
        else:
            logger.info("민감한 정보가 발견되지 않았습니다.")
        
        return self.findings
    
    def print_findings(self) -> None:
        """결과 출력"""
        if not self.findings:
            print("민감한 정보가 발견되지 않았습니다.")
            return
        
        print("\n" + "=" * 80)
        print(f"발견된 민감한 정보: {len(self.findings)}개")
        print("=" * 80)
        
        for i, finding in enumerate(self.findings, 1):
            print(f"\n[{i}] {finding['file']}:{finding['line']}")
            print(f"  키: {finding['key']}")
            print(f"  값: {finding['value']}")
            print(f"  엔트로피: {finding['entropy']:.2f}")
            print(f"  내용: {finding['line_content']}")
        
        print("\n" + "=" * 80)
        print("참고: 이 결과에는 오탐지가 포함될 수 있습니다.")
        print("각 발견 항목을 검토하고 필요한 조치를 취하세요.")
        print("=" * 80 + "\n")


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='프로젝트에서 하드코딩된 API 키, 토큰, 비밀번호 등 민감한 정보를 감지합니다.'
    )
    
    parser.add_argument(
        '--path', '-p',
        type=str,
        default='.',
        help='스캔할 프로젝트 경로 (기본값: 현재 디렉토리)'
    )
    
    parser.add_argument(
        '--exclude-dirs', '-d',
        type=str,
        nargs='+',
        default=DEFAULT_EXCLUDES,
        help='제외할 디렉토리 목록'
    )
    
    parser.add_argument(
        '--exclude-files', '-f',
        type=str,
        nargs='+',
        default=[],
        help='제외할 파일 목록'
    )
    
    parser.add_argument(
        '--exclude-patterns', '-e',
        type=str,
        nargs='+',
        default=[],
        help='제외할 패턴 목록 (정규식)'
    )
    
    parser.add_argument(
        '--min-entropy', '-m',
        type=float,
        default=3.5,
        help='최소 엔트로피 값 (기본값: 3.5)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='결과를 저장할 파일 경로 (JSON 형식)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로깅 활성화'
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 프로젝트 루트 경로
    project_root = Path(args.path).resolve()
    
    # 민감한 정보 감지기 초기화
    detector = SecretDetector(
        project_root=project_root,
        exclude_dirs=args.exclude_dirs,
        exclude_files=args.exclude_files,
        exclude_patterns=args.exclude_patterns,
        min_entropy=args.min_entropy,
        output_file=args.output,
        verbose=args.verbose
    )
    
    # 스캔 실행
    detector.run()
    
    # 결과 출력
    detector.print_findings()


if __name__ == '__main__':
    main()
