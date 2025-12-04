"""마크다운 변환 모듈"""
import re
from pathlib import Path
from .pdf_reader import Section, MergedSection


class MarkdownConverter:
    """텍스트와 표를 마크다운으로 변환"""

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """파일명으로 사용 가능하도록 문자열 정리"""
        # 파일명에 사용할 수 없는 문자 제거
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        # 공백을 언더스코어로
        sanitized = sanitized.replace(' ', '_')
        # 연속된 언더스코어 정리
        sanitized = re.sub(r'_+', '_', sanitized)
        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip('_')
        return sanitized[:50] if sanitized else "untitled"

    @staticmethod
    def text_to_markdown(text: str, section_title: str = None) -> str:
        """텍스트를 마크다운 형식으로 정리

        Args:
            text: 변환할 텍스트
            section_title: 섹션 제목 (중복 제거용)

        Returns:
            정리된 마크다운 텍스트
        """
        # 1. 단독 페이지 번호 제거 (한 줄에 숫자만 있는 경우)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

        # 2. 섹션 제목 중복 제거 (첫 줄이 제목과 동일한 경우)
        if section_title:
            lines = text.split('\n')
            # 빈 줄 제거하고 첫 번째 실제 내용 찾기
            non_empty_lines = [l for l in lines if l.strip()]
            if non_empty_lines:
                first_line = non_empty_lines[0].strip()
                # 제목에서 번호 부분 제거하여 비교 (예: "3.9.5 Keep Alive" -> "Keep Alive")
                title_without_number = re.sub(r'^[\d.]+\s*', '', section_title).strip()
                if first_line == title_without_number or first_line == section_title:
                    # 첫 번째 일치하는 줄 제거
                    for i, line in enumerate(lines):
                        if line.strip() == first_line:
                            lines[i] = ''
                            break
                    text = '\n'.join(lines)

        # 3. 연속된 빈 줄을 하나로
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 4. 앞뒤 공백 정리
        text = text.strip()
        return text

    @staticmethod
    def _clean_cell(cell: str) -> str:
        """셀 내용 정리 - 줄바꿈을 공백으로, 파이프 이스케이프"""
        if not cell:
            return ""
        # 줄바꿈을 공백으로 변환
        cleaned = str(cell).replace('\n', ' ').replace('\r', ' ')
        # 연속 공백 제거
        cleaned = ' '.join(cleaned.split())
        # 마크다운 테이블 파이프 이스케이프
        cleaned = cleaned.replace('|', '\\|')
        return cleaned.strip()

    @staticmethod
    def _clean_table(table: list[list[str]]) -> list[list[str]]:
        """표에서 빈 열 제거 및 데이터 정리"""
        if not table or not table[0]:
            return []

        num_cols = len(table[0])

        # 각 열이 완전히 비어있는지 확인
        empty_cols = set()
        for col_idx in range(num_cols):
            is_empty = all(
                not (MarkdownConverter._clean_cell(row[col_idx]) if col_idx < len(row) and row[col_idx] else "")
                for row in table
            )
            if is_empty:
                empty_cols.add(col_idx)

        # 빈 열 제거하고 새 표 생성
        cleaned = []
        for row in table:
            cleaned_row = [
                MarkdownConverter._clean_cell(cell)
                for idx, cell in enumerate(row)
                if idx not in empty_cols
            ]
            if cleaned_row and any(c for c in cleaned_row):  # 완전히 빈 행 제외
                cleaned.append(cleaned_row)

        return cleaned

    @staticmethod
    def table_to_markdown(table: list[list[str]]) -> str:
        """2D 리스트를 마크다운 테이블로 변환"""
        if not table or not table[0]:
            return ""

        # 빈 열 제거
        table = MarkdownConverter._clean_table(table)
        if not table or not table[0]:
            return ""

        lines = []

        # 헤더 행 (이미 _clean_table에서 정리됨)
        header = table[0]
        lines.append("| " + " | ".join(header) + " |")

        # 구분선
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # 데이터 행 (이미 _clean_table에서 정리됨)
        for row in table[1:]:
            # 열 수 맞추기
            cells = list(row)
            while len(cells) < len(header):
                cells.append("")
            lines.append("| " + " | ".join(cells[:len(header)]) + " |")

        return "\n".join(lines)

    def convert_section(
        self,
        section: Section,
        text: str,
        tables: list[list[list[str]]],
        index: int
    ) -> str:
        """섹션을 마크다운 문서로 변환"""
        lines = []

        # 섹션 제목 (레벨에 따라 # 개수 조절)
        heading = "#" * min(section.level, 6)
        lines.append(f"{heading} {section.title}")
        lines.append("")

        # 텍스트 내용 (섹션 제목 전달하여 중복 제거)
        md_text = self.text_to_markdown(text, section_title=section.title)
        if md_text:
            lines.append(md_text)
            lines.append("")

        # 표 추가
        for i, table in enumerate(tables):
            md_table = self.table_to_markdown(table)
            if md_table:
                lines.append(md_table)
                lines.append("")

        return "\n".join(lines)

    def generate_filename(self, section: Section, index: int) -> str:
        """섹션에 대한 파일명 생성"""
        safe_title = self.sanitize_filename(section.title)
        return f"{safe_title}.md"

    def save_section(
        self,
        output_dir: Path,
        section: Section,
        text: str,
        tables: list[list[list[str]]],
        index: int
    ) -> Path:
        """섹션을 마크다운 파일로 저장"""
        filename = self.generate_filename(section, index)
        filepath = output_dir / filename

        content = self.convert_section(section, text, tables, index)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def convert_merged_section(
        self,
        merged: MergedSection,
        section_contents: dict[str, tuple[str, list[list[list[str]]]]],
        index: int
    ) -> str:
        """
        병합된 섹션을 마크다운 문서로 변환

        Args:
            merged: 병합된 섹션 정보
            section_contents: 섹션 제목 -> (텍스트, 테이블) 매핑
            index: 인덱스

        Returns:
            마크다운 문자열
        """
        lines = []

        # 부모 섹션 내용
        parent = merged.parent
        heading = "#" * min(parent.level, 6)
        lines.append(f"{heading} {parent.title}")
        lines.append("")

        parent_key = parent.title
        if parent_key in section_contents:
            text, tables = section_contents[parent_key]
            md_text = self.text_to_markdown(text, section_title=parent.title)
            if md_text:
                lines.append(md_text)
                lines.append("")

            for table in tables:
                md_table = self.table_to_markdown(table)
                if md_table:
                    lines.append(md_table)
                    lines.append("")

        # 자식 섹션들 내용 추가
        for child in merged.children:
            child_heading = "#" * min(child.level, 6)
            lines.append(f"{child_heading} {child.title}")
            lines.append("")

            child_key = child.title
            if child_key in section_contents:
                text, tables = section_contents[child_key]
                md_text = self.text_to_markdown(text, section_title=child.title)
                if md_text:
                    lines.append(md_text)
                    lines.append("")

                for table in tables:
                    md_table = self.table_to_markdown(table)
                    if md_table:
                        lines.append(md_table)
                        lines.append("")

        return "\n".join(lines)

    def save_merged_section(
        self,
        output_dir: Path,
        merged: MergedSection,
        section_contents: dict[str, tuple[str, list[list[list[str]]]]],
        index: int
    ) -> Path:
        """병합된 섹션을 마크다운 파일로 저장"""
        filename = self.generate_filename(merged.parent, index)
        filepath = output_dir / filename

        content = self.convert_merged_section(merged, section_contents, index)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath
