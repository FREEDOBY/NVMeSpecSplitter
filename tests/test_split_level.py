"""분리 레벨 선택 기능 테스트"""
import pytest
from dataclasses import dataclass
from typing import Optional

# 테스트 대상 모듈 import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pdf_reader import Section, PDFReader, MergedSection, get_max_level, merge_sections_by_level


class TestGetMaxLevel:
    """TC-001: get_max_level() 테스트"""

    def test_max_level_with_multiple_levels(self):
        """여러 레벨이 있을 때 최대 레벨 반환"""
        sections = [
            Section(title="Chapter 1", level=1, start_page=0, end_page=10),
            Section(title="Section 1.1", level=2, start_page=0, end_page=5),
            Section(title="Subsection 1.1.1", level=3, start_page=0, end_page=2),
            Section(title="Chapter 2", level=1, start_page=11, end_page=20),
        ]
        assert get_max_level(sections) == 3

    def test_max_level_single_level(self):
        """단일 레벨만 있을 때"""
        sections = [
            Section(title="Chapter 1", level=1, start_page=0, end_page=10),
            Section(title="Chapter 2", level=1, start_page=11, end_page=20),
        ]
        assert get_max_level(sections) == 1

    def test_max_level_empty_sections(self):
        """빈 섹션 리스트"""
        sections = []
        assert get_max_level(sections) == 0

    def test_max_level_deep_nesting(self):
        """깊은 중첩 레벨"""
        sections = [
            Section(title="L1", level=1, start_page=0, end_page=100),
            Section(title="L2", level=2, start_page=0, end_page=50),
            Section(title="L3", level=3, start_page=0, end_page=25),
            Section(title="L4", level=4, start_page=0, end_page=12),
            Section(title="L5", level=5, start_page=0, end_page=6),
        ]
        assert get_max_level(sections) == 5


class TestMergeSections:
    """TC-002~004: 섹션 병합 테스트"""

    @pytest.fixture
    def sample_sections(self):
        """테스트용 섹션 데이터"""
        return [
            Section(title="Chapter 1", level=1, start_page=0, end_page=10),
            Section(title="Section 1.1", level=2, start_page=0, end_page=5),
            Section(title="Subsection 1.1.1", level=3, start_page=0, end_page=2),
            Section(title="Subsection 1.1.2", level=3, start_page=3, end_page=5),
            Section(title="Section 1.2", level=2, start_page=6, end_page=10),
            Section(title="Chapter 2", level=1, start_page=11, end_page=20),
            Section(title="Section 2.1", level=2, start_page=11, end_page=15),
        ]

    def test_merge_level_1(self, sample_sections):
        """레벨 1 선택 시 - 최상위 섹션만 파일로 분리"""
        merged = merge_sections_by_level(sample_sections, split_level=1)

        # 2개의 병합 섹션 (Chapter 1, Chapter 2)
        assert len(merged) == 2

        # Chapter 1에 하위 섹션들 포함
        assert merged[0].parent.title == "Chapter 1"
        assert len(merged[0].children) == 4  # 1.1, 1.1.1, 1.1.2, 1.2

        # Chapter 2에 하위 섹션 포함
        assert merged[1].parent.title == "Chapter 2"
        assert len(merged[1].children) == 1  # 2.1

    def test_merge_level_2(self, sample_sections):
        """레벨 2 선택 시 - 레벨 1, 2만 파일로 분리"""
        merged = merge_sections_by_level(sample_sections, split_level=2)

        # 5개의 병합 섹션 (Ch1, 1.1, 1.2, Ch2, 2.1)
        assert len(merged) == 5

        # Section 1.1에 하위 섹션들 포함
        section_1_1 = next(m for m in merged if m.parent.title == "Section 1.1")
        assert len(section_1_1.children) == 2  # 1.1.1, 1.1.2

        # Chapter 1은 자체 내용만 (하위 레벨 2 섹션은 별도 파일)
        chapter_1 = next(m for m in merged if m.parent.title == "Chapter 1")
        assert len(chapter_1.children) == 0

    def test_merge_all_levels(self, sample_sections):
        """모든 레벨 선택 시 - 기존 동작 (각각 개별 파일)"""
        merged = merge_sections_by_level(sample_sections, split_level=None)

        # 7개 모두 개별
        assert len(merged) == 7
        for m in merged:
            assert len(m.children) == 0

    def test_merge_level_3(self, sample_sections):
        """레벨 3 선택 시 - 모든 레벨 개별 파일 (최대 레벨이 3이므로)"""
        merged = merge_sections_by_level(sample_sections, split_level=3)

        # 7개 모두 개별 (하위 레벨이 없으므로)
        assert len(merged) == 7

    def test_merge_empty_sections(self):
        """빈 섹션 리스트"""
        merged = merge_sections_by_level([], split_level=1)
        assert len(merged) == 0


class TestMergedSectionContent:
    """TC-006: 병합된 마크다운 내용 검증"""

    @pytest.fixture
    def sections_with_content(self):
        """콘텐츠가 있는 테스트용 섹션"""
        return [
            Section(title="Chapter 1", level=1, start_page=0, end_page=10),
            Section(title="Section 1.1", level=2, start_page=0, end_page=5),
            Section(title="Subsection 1.1.1", level=3, start_page=0, end_page=2),
        ]

    def test_merged_markdown_contains_all_headings(self, sections_with_content):
        """병합된 마크다운에 모든 제목 포함 확인"""
        merged = merge_sections_by_level(sections_with_content, split_level=1)

        # 병합 결과 확인
        assert len(merged) == 1
        assert merged[0].parent.title == "Chapter 1"
        assert len(merged[0].children) == 2

        # 자식 섹션 제목 확인
        child_titles = [c.title for c in merged[0].children]
        assert "Section 1.1" in child_titles
        assert "Subsection 1.1.1" in child_titles


class TestEdgeCases:
    """TC-005: 엣지 케이스 테스트"""

    def test_gap_in_levels(self):
        """레벨 간 격차 (1, 3 존재, 2 없음)"""
        sections = [
            Section(title="Chapter 1", level=1, start_page=0, end_page=10),
            Section(title="Deep Section", level=3, start_page=0, end_page=5),  # 레벨 2 건너뜀
        ]
        merged = merge_sections_by_level(sections, split_level=1)

        assert len(merged) == 1
        assert merged[0].parent.title == "Chapter 1"
        assert len(merged[0].children) == 1

    def test_single_section(self):
        """단일 섹션"""
        sections = [
            Section(title="Only Section", level=1, start_page=0, end_page=10),
        ]
        merged = merge_sections_by_level(sections, split_level=1)

        assert len(merged) == 1
        assert merged[0].parent.title == "Only Section"
        assert len(merged[0].children) == 0

    def test_split_level_greater_than_max(self):
        """split_level이 최대 레벨보다 큰 경우"""
        sections = [
            Section(title="Chapter 1", level=1, start_page=0, end_page=10),
            Section(title="Section 1.1", level=2, start_page=0, end_page=5),
        ]
        merged = merge_sections_by_level(sections, split_level=10)

        # 모든 섹션 개별 파일
        assert len(merged) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
