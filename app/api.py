"""接口层（FastAPI），我最喜欢的环节，孩子们还是这个直观

接口分组：
    /api/books      图书的查、增、改、删
    /api/borrows    借阅、归还、记录列表
    /api/stats      统计信息

状态码约定：
    200      成功
    201      创建成功
    400      业务规则冲突（如 ISBN 重复、库存不足、仍有未归还记录）
    404      资源不存在
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel

from . import crud
from .config import APP_TITLE, DEFAULT_PAGE_SIZE, WEB_DIR
from .db import get_session, init_db
from .seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    #feat：服务启动时建表并写入演示数据，关闭时无需额外清理
    init_db()
    seed()
    yield


app = FastAPI(
    title=APP_TITLE,
    version="1.0.0",
    description="图书管理系统后端接口",
    lifespan=lifespan,
)

class BookIn(SQLModel):
    #新增图书请求
    isbn: str
    title: str
    author: str = ""
    publisher: str = ""
    category: str = ""
    price: float = 0.0
    stock: int = 0

class BookPatch(SQLModel):
    #更新图书请求
    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None

class BorrowIn(SQLModel):
    #借阅请求
    book_id: int
    borrower: str

def _bad_request(error: ValueError) -> HTTPException:
    #把业务异常统一转换为400响应，知道是内部错误就行管那么多干嘛
    return HTTPException(status_code=400, detail=str(error))

@app.get("/api/books", summary="分页查询图书")
def api_list_books(
    kw: str = "",
    page: int = 1,
    size: int = DEFAULT_PAGE_SIZE,
    session: Session = Depends(get_session),
):
    rows, total = crud.list_books(session, keyword=kw, page=page, size=size)
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [row.model_dump() for row in rows],
    }

@app.get("/api/books/{book_id}", summary="按主键查询单本图书")
def api_get_book(book_id: int, session: Session = Depends(get_session)):
    try:
        return crud.get_book(session, book_id).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.post("/api/books", status_code=201, summary="新增图书")
def api_create_book(payload: BookIn, session: Session = Depends(get_session)):
    try:
        return crud.create_book(session, payload.model_dump()).model_dump()
    except ValueError as exc:
        raise _bad_request(exc) from exc

@app.put("/api/books/{book_id}", summary="修改图书")
def api_update_book(
    book_id: int,
    payload: BookPatch,
    session: Session = Depends(get_session),
):
    #未传的字段不参与更新，避免被默认值覆盖
    data = payload.model_dump(exclude_unset=True)
    try:
        return crud.update_book(session, book_id, data).model_dump()
    except ValueError as exc:
        raise _bad_request(exc) from exc

@app.delete("/api/books/{book_id}", summary="删除图书")
def api_delete_book(book_id: int, session: Session = Depends(get_session)):
    try:
        crud.delete_book(session, book_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return {"ok": True, "message": "删除成功"}

@app.post("/api/borrows", status_code=201, summary="借出图书")
def api_borrow(payload: BorrowIn, session: Session = Depends(get_session)):
    try:
        return crud.borrow_book(session, payload.book_id, payload.borrower).model_dump()
    except ValueError as exc:
        raise _bad_request(exc) from exc

@app.post("/api/borrows/{borrow_id}/return", summary="归还图书")
def api_return(borrow_id: int, session: Session = Depends(get_session)):
    try:
        return crud.return_book(session, borrow_id).model_dump()
    except ValueError as exc:
        raise _bad_request(exc) from exc

@app.get("/api/borrows", summary="借阅记录列表")
def api_list_borrows(
    unreturned: bool = False,
    session: Session = Depends(get_session),
):
    rows = crud.list_borrows(session, only_unreturned=unreturned)
    return {"total": len(rows), "items": [row.model_dump() for row in rows]}

@app.get("/api/stats", summary="概览统计")
def api_stats(session: Session = Depends(get_session)):
    return crud.stats(session)

#静态资源挂载，py这个倒是挺讨我喜欢
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
