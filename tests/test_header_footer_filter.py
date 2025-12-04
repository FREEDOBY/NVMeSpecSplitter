"""헤더/푸터 필터링 기능 테스트"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.md_converter import MarkdownConverter
from core.pdf_reader import HEADER_MARGIN, FOOTER_MARGIN


class TestPageNumberRemoval:
    """TC-HF-001~003: 페이지 번호 제거 테스트"""

    def test_remove_standalone_page_number(self):
        """TC-HF-001: 단독 숫자 라인 제거"""
        text = "Some content\n127\nMore content"
        result = MarkdownConverter.text_to_markdown(text)
        assert "127" not in result
        assert "Some content" in result
        assert "More content" in result

    def test_remove_page_number_with_whitespace(self):
        """TC-HF-002: 공백 포함 숫자 라인 제거"""
        text = "Content before\n  42  \nContent after"
        result = MarkdownConverter.text_to_markdown(text)
        assert "42" not in result
        assert "Content before" in result
        assert "Content after" in result

    def test_preserve_numbers_in_text(self):
        """TC-HF-003: 본문 내 숫자는 유지"""
        text = "The value is 127 bytes.\nAnother line with 42 items."
        result = MarkdownConverter.text_to_markdown(text)
        assert "127 bytes" in result
        assert "42 items" in result

    def test_remove_multiple_page_numbers(self):
        """여러 페이지 번호 제거"""
        text = "Page 1 content\n1\nPage 2 content\n2\nPage 3 content\n3\n"
        result = MarkdownConverter.text_to_markdown(text)
        # 단독 숫자 라인만 제거, 문장 내 숫자는 유지
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "Page 3 content" in result
        # 단독 숫자는 제거됨
        lines = result.split('\n')
        standalone_numbers = [line for line in lines if line.strip().isdigit()]
        assert len(standalone_numbers) == 0


class TestDuplicateTitleRemoval:
    """TC-HF-004: 섹션 제목 중복 제거 테스트"""

    def test_remove_duplicate_title_without_number(self):
        """제목 중복 제거 - 번호 없는 제목"""
        text = "Keep Alive Timeout Cleanup\nThis is the actual content."
        result = MarkdownConverter.text_to_markdown(text, section_title="3.9.5 Keep Alive Timeout Cleanup")
        assert "Keep Alive Timeout Cleanup" not in result.split('\n')[0] if result else True
        assert "actual content" in result

    def test_remove_duplicate_title_exact_match(self):
        """제목 중복 제거 - 정확히 일치"""
        text = "Introduction\nThis is the introduction section."
        result = MarkdownConverter.text_to_markdown(text, section_title="Introduction")
        lines = result.split('\n')
        # 첫 줄이 "Introduction"이 아니어야 함
        assert lines[0].strip() != "Introduction"
        assert "introduction section" in result

    def test_preserve_title_when_different(self):
        """제목이 다르면 유지"""
        text = "Different Title\nThis is the content."
        result = MarkdownConverter.text_to_markdown(text, section_title="3.9.5 Keep Alive")
        assert "Different Title" in result
        assert "content" in result

    def test_no_title_provided(self):
        """section_title이 None일 때 제거 안함"""
        text = "Some Title\nContent here."
        result = MarkdownConverter.text_to_markdown(text, section_title=None)
        assert "Some Title" in result
        assert "Content here" in result


class TestMarginConstants:
    """TC-HF-005~006: 헤더/푸터 여백 상수 테스트"""

    def test_header_margin_exists(self):
        """TC-HF-005: 헤더 여백 상수 존재"""
        assert HEADER_MARGIN is not None
        assert HEADER_MARGIN > 0
        assert HEADER_MARGIN == 50.0  # 50pt

    def test_footer_margin_exists(self):
        """TC-HF-006: 푸터 여백 상수 존재"""
        assert FOOTER_MARGIN is not None
        assert FOOTER_MARGIN > 0
        assert FOOTER_MARGIN == 50.0  # 50pt


class TestEmptyTextHandling:
    """TC-HF-007: 빈 텍스트 처리 테스트"""

    def test_empty_string(self):
        """빈 문자열 처리"""
        result = MarkdownConverter.text_to_markdown("")
        assert result == ""

    def test_only_whitespace(self):
        """공백만 있는 경우"""
        result = MarkdownConverter.text_to_markdown("   \n\n   ")
        assert result == ""

    def test_only_page_numbers(self):
        """페이지 번호만 있는 경우"""
        result = MarkdownConverter.text_to_markdown("1\n2\n3\n")
        assert result == ""


class TestIntegration:
    """TC-HF-008: 통합 테스트"""

    def test_full_pipeline_with_page_numbers_and_duplicate_title(self):
        """전체 파이프라인 - 페이지 번호 + 중복 제목"""
        text = """127

Keep Alive Timeout Cleanup

The Keep Alive feature maintains the connection between
the host and the controller. This section describes the
timeout cleanup process.

128

When a timeout occurs, the following steps are taken:
1. Connection state is checked
2. Resources are freed
"""
        result = MarkdownConverter.text_to_markdown(
            text,
            section_title="3.9.5 Keep Alive Timeout Cleanup"
        )

        # 페이지 번호 제거됨
        assert "\n127\n" not in result
        assert "\n128\n" not in result

        # 중복 제목 제거됨 (첫 줄)
        lines = result.strip().split('\n')
        assert lines[0].strip() != "Keep Alive Timeout Cleanup"

        # 본문 내용 유지
        assert "Keep Alive feature" in result
        assert "timeout cleanup process" in result
        assert "Connection state is checked" in result

    def test_preserves_numbered_lists(self):
        """번호 목록은 유지"""
        text = "Steps:\n1. First step\n2. Second step\n3. Third step"
        result = MarkdownConverter.text_to_markdown(text)
        assert "1. First step" in result
        assert "2. Second step" in result
        assert "3. Third step" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
