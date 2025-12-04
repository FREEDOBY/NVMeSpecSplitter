"""마크다운 변환 모듈"""
import re
from pathlib import Path
from .pdf_reader import Section


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
    def text_to_markdown(text: str) -> str:
        """텍스트를 마크다운 형식으로 정리"""
        # 연속된 빈 줄을 하나로
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 앞뒤 공백 정리
        text = text.strip()
        return text

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
                not (str(row[col_idx]).strip() if col_idx < len(row) and row[col_idx] else "")
                for row in table
            )
            if is_empty:
                empty_cols.add(col_idx)

        # 빈 열 제거하고 새 표 생성
        cleaned = []
        for row in table:
            cleaned_row = [
                str(cell).strip() if cell else ""
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

        # 헤더 행
        header = table[0]
        header_cells = [str(cell) if cell else "" for cell in header]
        lines.append("| " + " | ".join(header_cells) + " |")

        # 구분선
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # 데이터 행
        for row in table[1:]:
            cells = [str(cell) if cell else "" for cell in row]
            # 열 수 맞추기
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

        # 텍스트 내용
        md_text = self.text_to_markdown(text)
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
