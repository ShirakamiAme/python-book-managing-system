#业务逻辑层：图书与借阅记录的查询、增、删、改、借、还。
from datetime import date, timedelta
from typing import Optional

from sqlmodel import Session, func, select

from .models import Book, Borrow

#默认借期
LOAN_DAYS: int = 30

def list_books(
    session: Session,
    keyword: str = "",
    page: int = 1,
    size: int = 20,
) -> tuple[list[Book], int]:
    """
    分页查询图书
    keyword 同时模糊匹配书名、作者与 ISBN。
    返回 (当前页数据, 总条数)，总条数供前端计算页数
    """
    stmt = select(Book)
    keyword = (keyword or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            (Book.title.like(pattern))
            | (Book.author.like(pattern))
            | (Book.isbn.like(pattern))
        )

    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()

    page = max(page, 1)
    size = min(max(size, 1), 100)
    rows = session.exec(
        stmt.order_by(Book.id).offset((page - 1) * size).limit(size)
    ).all()
    return list(rows), int(total)


def get_book(session: Session, book_id: int) -> Book:
    #按主键取书，不存在则报错
    book = session.get(Book, book_id)
    if book is None:
        raise ValueError(f"图书不存在（id={book_id}）")
    return book

def create_book(session: Session, data: dict) -> Book:
    #新增图书，ISBN唯一
    isbn = str(data.get("isbn", "")).strip()
    if not isbn:
        raise ValueError("ISBN 不能为空")
    if session.exec(select(Book).where(Book.isbn == isbn)).first() is not None:
        raise ValueError(f"ISBN 已存在：{isbn}")

    book = Book(**{**data, "isbn": isbn})
    session.add(book)
    session.commit()
    session.refresh(book)
    return book

def update_book(session: Session, book_id: int, data: dict) -> Book:
    #按主键更新图书，仅覆盖传入的字段
    book = get_book(session, book_id)

    new_isbn = data.get("isbn")
    if new_isbn is not None:
        new_isbn = str(new_isbn).strip()
        if not new_isbn:
            raise ValueError("ISBN 不能为空")
        if new_isbn != book.isbn:
            duplicated = session.exec(
                select(Book).where(Book.isbn == new_isbn)
            ).first()
            if duplicated is not None:
                raise ValueError(f"ISBN 已存在：{new_isbn}")
        data["isbn"] = new_isbn

    for field, value in data.items():
        if value is not None and hasattr(book, field):
            setattr(book, field, value)

    session.add(book)
    session.commit()
    session.refresh(book)
    return book

def delete_book(session: Session, book_id: int) -> None:
    #删除图书；存在未归还记录时禁止删除
    book = get_book(session, book_id)
    active = session.exec(
        select(Borrow).where(
            Borrow.book_id == book_id,
            Borrow.returned == False,  # noqa: E712  与 SQL 语义一致
        )
    ).first()
    if active is not None:
        raise ValueError("该书仍有未归还的借阅记录，无法删除")

    session.delete(book)
    session.commit()

def borrow_book(session: Session, book_id: int, borrower: str) -> Borrow:
    #借出
    borrower = (borrower or "").strip()
    if not borrower:
        raise ValueError("借阅人不能为空")

    book = get_book(session, book_id)
    if book.stock <= 0:
        raise ValueError(f"《{book.title}》库存不足，暂无法借出")

    book.stock -= 1#在库-1，然后创建一条记录加进去
    record = Borrow(
        book_id=book.id,
        book_title=book.title,
        borrower=borrower,
        due_date=date.today() + timedelta(days=LOAN_DAYS),
    )
    session.add(book)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record

def return_book(session: Session, borrow_id: int) -> Borrow:
    #归还图书，先找记录
    record = session.get(Borrow, borrow_id)
    if record is None:
        raise ValueError(f"借阅记录不存在（id={borrow_id}）")
    if record.returned:
        raise ValueError("该记录已归还，无需重复操作")

    record.returned = True
    record.return_date = date.today()
    session.add(record)
    #库存喜加一
    book = session.get(Book, record.book_id)
    if book is not None:
        book.stock += 1
        session.add(book)

    session.commit()
    session.refresh(record)
    return record

def list_borrows(session: Session, only_unreturned: bool = False) -> list[Borrow]:
    #借阅记录列表
    stmt = select(Borrow)
    if only_unreturned:
        stmt = stmt.where(Borrow.returned == False)
    return list(session.exec(stmt.order_by(Borrow.id.desc())).all())

def stats(session: Session) -> dict:
    #顶部状态栏用的
    total_books = session.exec(select(func.count()).select_from(Book)).one()
    total_stock = session.exec(select(func.coalesce(func.sum(Book.stock), 0))).one()
    borrowing = session.exec(
        select(func.count()).select_from(Borrow).where(Borrow.returned == False)
    ).one()
    return {
        "total_books": int(total_books),
        "total_stock": int(total_stock),
        "borrowing": int(borrowing),
    }

"""
Note：我当然知道这种东西不该写在注释里面，但是摸着良心说，我是真讨厌py关于类型的处理，太宽松了IDE反而有事没事黄两下，丑死了:(
"""