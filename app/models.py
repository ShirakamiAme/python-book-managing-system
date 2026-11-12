#搓半个MVC咯
from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Book(SQLModel, table=True):
    #图书信息表

    __tablename__ = "book"

    id: Optional[int] = Field(default=None, primary_key=True, description="主键")
    isbn: str = Field(index=True, unique=True, max_length=32, description="ISBN，全馆唯一")
    title: str = Field(index=True, max_length=128, description="书名")
    author: str = Field(default="", max_length=64, description="作者")
    publisher: str = Field(default="", max_length=64, description="出版社")
    category: str = Field(default="", max_length=32, description="图书分类")
    price: float = Field(default=0.0, ge=0, description="定价（元）")
    # 借出时减一、归还时加一；为0暂无在库可借
    stock: int = Field(default=0, ge=0, index=True, description="当前在库数量")


class Borrow(SQLModel, table=True):
    #借阅记录表

    __tablename__ = "borrow"

    id: Optional[int] = Field(default=None, primary_key=True, description="主键")
    book_id: int = Field(foreign_key="book.id", index=True, description="外键，指向 book.id")
    #冗余存一份书名，列表展示时，无需再关联查询
    book_title: str = Field(default="", max_length=128, description="书名快照")
    borrower: str = Field(max_length=64, index=True, description="借阅人姓名")
    borrow_date: date = Field(default_factory=date.today, description="借出日期")
    due_date: Optional[date] = Field(default=None, description="应还日期")
    return_date: Optional[date] = Field(default=None, description="实际归还日期")
    returned: bool = Field(default=False, index=True, description="是否已归还")
