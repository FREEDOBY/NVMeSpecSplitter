"""PDF to Markdown Splitter - 진입점"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from gui.app import run


if __name__ == "__main__":
    run()
