import os
from pathlib import Path
#路径相关
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
WEB_DIR: Path = BASE_DIR / "web"
DB_PATH: Path = Path(os.environ.get("LIB_DB_PATH") or (DATA_DIR / "library.db"))#本来是不用写这个的，但是大D牢史建议我还是写个允许替换用于测试比较好，虽然我也用不上就是了(

#确保数据目录存在，否则sqlite那边会报错
DATA_DIR.mkdir(parents=True, exist_ok=True)

#界面配置
APP_TITLE: str = "图书管理系统"
WINDOW_WIDTH: int = 1280
WINDOW_HEIGHT: int = 720

#分页默认值
DEFAULT_PAGE_SIZE: int = 20
