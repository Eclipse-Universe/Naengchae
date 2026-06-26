import sys
from pathlib import Path

# 패키지를 pip install 하지 않고 바로 import할 수 있도록 경로에 추가합니다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
