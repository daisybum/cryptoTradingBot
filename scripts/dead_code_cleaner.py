#!/usr/bin/env python3
"""
Dead Code Cleaner

이 스크립트는 Vulture를 사용하여 프로젝트에서 사용되지 않는 코드(dead code)를 찾고,
사용자의 선택에 따라 이를 제거하거나 주석 처리합니다.

사용법:
    python dead_code_cleaner.py [options]

옵션:
    --scan              : 사용되지 않는 코드만 스캔하고 보고서 생성 (기본 모드)
    --comment           : 사용되지 않는 코드를 주석 처리
    --remove            : 사용되지 않는 코드 제거 (주의: 되돌릴 수 없음)
    --whitelist FILE    : 화이트리스트 파일 지정 (기본: whitelist.py)
    --min-confidence N  : 최소 신뢰도 설정 (0-100, 기본: 60)
    --path PATH         : 스캔할 경로 지정 (기본: src)
    --exclude PATTERN   : 제외할 패턴 지정 (예: "*test*,*settings.py")
    --backup            : 변경 전 파일 백업
    --report FILE       : 보고서 저장 파일 지정 (기본: dead_code_report.md)
"""

import os
import sys
import re
import shutil
import argparse
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional

# 색상 코드
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DeadCodeItem:
    """사용되지 않는 코드 항목을 나타내는 클래스"""
    
    def __init__(self, file_path: str, line: int, code_type: str, name: str, confidence: int):
        self.file_path = file_path
        self.line = line
        self.code_type = code_type
        self.name = name
        self.confidence = confidence
        self.content = ""  # 코드 내용
        self.context_lines = []  # 주변 코드 라인
    
    def __str__(self) -> str:
        return f"{self.file_path}:{self.line}: unused {self.code_type} '{self.name}' ({self.confidence}% confidence)"

class DeadCodeCleaner:
    """사용되지 않는 코드를 찾고 정리하는 클래스"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.dead_code_items: List[DeadCodeItem] = []
        self.whitelist: List[str] = []
        self.files_with_changes: Dict[str, int] = {}
        
        # 화이트리스트 로드
        if os.path.exists(args.whitelist):
            with open(args.whitelist, 'r') as f:
                self.whitelist = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    def run_vulture(self) -> List[str]:
        """Vulture를 실행하여 사용되지 않는 코드 찾기"""
        cmd = [
            "vulture", 
            self.args.path, 
            f"--min-confidence={self.args.min_confidence}"
        ]
        
        if self.args.exclude:
            cmd.append(f"--exclude={self.args.exclude}")
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.splitlines()
        except Exception as e:
            print(f"{Colors.FAIL}Vulture 실행 중 오류 발생: {e}{Colors.ENDC}")
            sys.exit(1)
    
    def parse_vulture_output(self, output_lines: List[str]) -> None:
        """Vulture 출력 파싱하여 DeadCodeItem 객체 생성"""
        pattern = r"^(.+):(\d+): unused (\w+) '(.+)' \((\d+)% confidence\)$"
        
        for line in output_lines:
            match = re.match(pattern, line)
            if match:
                file_path, line_num, code_type, name, confidence = match.groups()
                
                # 화이트리스트 체크
                if any(re.search(pattern, name) for pattern in self.whitelist):
                    continue
                
                item = DeadCodeItem(
                    file_path=file_path,
                    line=int(line_num),
                    code_type=code_type,
                    name=name,
                    confidence=int(confidence)
                )
                
                # 코드 내용 및 컨텍스트 로드
                self.load_code_context(item)
                
                self.dead_code_items.append(item)
    
    def load_code_context(self, item: DeadCodeItem) -> None:
        """코드 항목의 내용과 주변 컨텍스트 로드"""
        try:
            with open(item.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if 0 <= item.line - 1 < len(lines):
                # 현재 라인
                item.content = lines[item.line - 1].rstrip()
                
                # 컨텍스트 라인 (현재 라인 전후 3줄)
                start = max(0, item.line - 4)
                end = min(len(lines), item.line + 3)
                item.context_lines = [(i+1, lines[i].rstrip()) for i in range(start, end)]
        except Exception as e:
            print(f"{Colors.WARNING}파일 읽기 오류 ({item.file_path}): {e}{Colors.ENDC}")
    
    def process_files(self) -> None:
        """파일 처리 (주석 처리 또는 제거)"""
        if self.args.scan:
            return  # 스캔 모드에서는 파일 수정 없음
        
        # 파일별로 그룹화
        files_to_process = {}
        for item in self.dead_code_items:
            if item.file_path not in files_to_process:
                files_to_process[item.file_path] = []
            files_to_process[item.file_path].append(item)
        
        # 각 파일 처리
        for file_path, items in files_to_process.items():
            try:
                # 파일 백업
                if self.args.backup:
                    backup_path = f"{file_path}.bak"
                    shutil.copy2(file_path, backup_path)
                    print(f"{Colors.BLUE}파일 백업 생성: {backup_path}{Colors.ENDC}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 라인 번호로 정렬 (역순으로 처리하여 라인 번호 변경 방지)
                items.sort(key=lambda x: x.line, reverse=True)
                
                changes_count = 0
                for item in items:
                    line_idx = item.line - 1
                    if 0 <= line_idx < len(lines):
                        if self.args.comment:
                            # 주석 처리
                            lines[line_idx] = f"# DEAD CODE: {lines[line_idx]}"
                            changes_count += 1
                        elif self.args.remove:
                            # 코드 제거
                            lines[line_idx] = f"# REMOVED DEAD CODE: {item.code_type} '{item.name}'\n"
                            changes_count += 1
                
                if changes_count > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    self.files_with_changes[file_path] = changes_count
                    print(f"{Colors.GREEN}파일 수정됨: {file_path} ({changes_count}개 항목){Colors.ENDC}")
            
            except Exception as e:
                print(f"{Colors.FAIL}파일 처리 오류 ({file_path}): {e}{Colors.ENDC}")
    
    def generate_report(self) -> None:
        """결과 보고서 생성"""
        report_lines = [
            f"# Dead Code 분석 보고서",
            f"",
            f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 요약",
            f"",
            f"- 총 발견된 항목: {len(self.dead_code_items)}개",
            f"- 영향 받은 파일: {len(set(item.file_path for item in self.dead_code_items))}개",
        ]
        
        if not self.args.scan:
            report_lines.extend([
                f"- 처리된 파일: {len(self.files_with_changes)}개",
                f"- 변경된 항목: {sum(self.files_with_changes.values())}개",
                f"- 처리 모드: {'주석 처리' if self.args.comment else '제거' if self.args.remove else '스캔만'}"
            ])
        
        # 코드 타입별 통계
        code_types = {}
        for item in self.dead_code_items:
            code_types[item.code_type] = code_types.get(item.code_type, 0) + 1
        
        report_lines.extend([
            f"",
            f"## 코드 타입별 통계",
            f"",
        ])
        
        for code_type, count in sorted(code_types.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"- {code_type}: {count}개")
        
        # 파일별 통계
        file_stats = {}
        for item in self.dead_code_items:
            file_stats[item.file_path] = file_stats.get(item.file_path, 0) + 1
        
        report_lines.extend([
            f"",
            f"## 파일별 통계",
            f"",
        ])
        
        for file_path, count in sorted(file_stats.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"- {file_path}: {count}개")
        
        # 상세 항목 목록
        report_lines.extend([
            f"",
            f"## 상세 항목 목록",
            f"",
        ])
        
        # 파일별로 그룹화
        items_by_file = {}
        for item in self.dead_code_items:
            if item.file_path not in items_by_file:
                items_by_file[item.file_path] = []
            items_by_file[item.file_path].append(item)
        
        for file_path, items in sorted(items_by_file.items()):
            report_lines.append(f"### {file_path}")
            report_lines.append(f"")
            
            for item in sorted(items, key=lambda x: x.line):
                report_lines.append(f"- 라인 {item.line}: unused {item.code_type} '{item.name}' ({item.confidence}% confidence)")
                report_lines.append(f"  ```python")
                report_lines.append(f"  {item.content}")
                report_lines.append(f"  ```")
                report_lines.append(f"")
        
        # 화이트리스트 추천
        if self.args.scan:
            report_lines.extend([
                f"## 화이트리스트 추천",
                f"",
                f"다음은 화이트리스트에 추가할 수 있는 항목입니다:",
                f"```python",
            ])
            
            for item in self.dead_code_items:
                if item.confidence < 80:  # 낮은 신뢰도 항목은 화이트리스트 추천
                    report_lines.append(f"{item.name}  # {item.file_path}:{item.line}")
            
            report_lines.append(f"```")
        
        # 보고서 저장
        with open(self.args.report, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"{Colors.GREEN}보고서가 생성되었습니다: {self.args.report}{Colors.ENDC}")
    
    def run(self) -> None:
        """전체 프로세스 실행"""
        print(f"{Colors.HEADER}Dead Code Cleaner 실행 중...{Colors.ENDC}")
        print(f"{Colors.BLUE}Vulture를 사용하여 사용되지 않는 코드 스캔 중...{Colors.ENDC}")
        
        vulture_output = self.run_vulture()
        if not vulture_output:
            print(f"{Colors.GREEN}사용되지 않는 코드가 발견되지 않았습니다.{Colors.ENDC}")
            return
        
        print(f"{Colors.BLUE}발견된 항목 분석 중...{Colors.ENDC}")
        self.parse_vulture_output(vulture_output)
        
        print(f"{Colors.BLUE}발견된 사용되지 않는 코드: {len(self.dead_code_items)}개{Colors.ENDC}")
        
        if not self.args.scan:
            mode = "주석 처리" if self.args.comment else "제거" if self.args.remove else "스캔만"
            print(f"{Colors.BLUE}모드: {mode}{Colors.ENDC}")
            
            if self.args.comment or self.args.remove:
                self.process_files()
        
        self.generate_report()
        print(f"{Colors.HEADER}Dead Code Cleaner 완료!{Colors.ENDC}")

def main():
    parser = argparse.ArgumentParser(description="Dead Code Cleaner - Vulture 기반 사용되지 않는 코드 정리 도구")
    
    # 동작 모드 (상호 배타적)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--scan", action="store_true", default=True, help="사용되지 않는 코드만 스캔 (기본 모드)")
    mode_group.add_argument("--comment", action="store_true", help="사용되지 않는 코드를 주석 처리")
    mode_group.add_argument("--remove", action="store_true", help="사용되지 않는 코드 제거 (주의: 되돌릴 수 없음)")
    
    # 기타 옵션
    parser.add_argument("--whitelist", default="whitelist.py", help="화이트리스트 파일 지정 (기본: whitelist.py)")
    parser.add_argument("--min-confidence", type=int, default=60, help="최소 신뢰도 설정 (0-100, 기본: 60)")
    parser.add_argument("--path", default="src", help="스캔할 경로 지정 (기본: src)")
    parser.add_argument("--exclude", help="제외할 패턴 지정 (예: '*test*,*settings.py')")
    parser.add_argument("--backup", action="store_true", help="변경 전 파일 백업")
    parser.add_argument("--report", default="dead_code_report.md", help="보고서 저장 파일 지정 (기본: dead_code_report.md)")
    
    args = parser.parse_args()
    
    # 스캔 모드가 기본값이므로, comment나 remove가 True면 scan은 False로 설정
    if args.comment or args.remove:
        args.scan = False
    
    cleaner = DeadCodeCleaner(args)
    cleaner.run()

if __name__ == "__main__":
    main()
