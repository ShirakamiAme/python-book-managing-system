#数据库连接与会话管理

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from .config import DB_PATH

"""
关于check_same_thread=False：
因为SQLite默认禁止跨线程复用同一连接，而uvicorn会把请求分发到工作线程，所以如果我不关了这该死的检查，调用接口时，ProgrammingError就会用靴子狠狠地踢我的屁股
安全？构造的作业你跟我讲这个
"""
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    #根据模型定义建表；表已存在时自动跳过，可重复调用。
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    #提供数据库会话，供FastAPI做DI的时候用；使用yield而非return，是为了让请求结束时自动关闭会话，避免连接泄漏，大D牢师教我的，说实话我也不知道这玩意靠不靠谱
    with Session(engine) as session:
        yield session
