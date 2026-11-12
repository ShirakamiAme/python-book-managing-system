#初始数据，ai写的模拟数据别太较真


from sqlmodel import Session, select

from .db import engine
from .models import Book, Borrow

SAMPLE_BOOKS: list[dict] = [
    {"isbn": "9787020002207", "title": "红楼梦", "author": "曹雪芹",
     "publisher": "人民文学出版社", "category": "古典文学", "price": 59.7, "stock": 4},
    {"isbn": "9787536692930", "title": "三体", "author": "刘慈欣",
     "publisher": "重庆出版社", "category": "科幻小说", "price": 23.0, "stock": 6},
    {"isbn": "9787115428028", "title": "Python编程从入门到实践", "author": "Eric Matthes",
     "publisher": "人民邮电出版社", "category": "计算机", "price": 89.8, "stock": 5},
    {"isbn": "9787111213826", "title": "算法导论", "author": "Thomas H. Cormen",
     "publisher": "机械工业出版社", "category": "计算机", "price": 128.0, "stock": 2},
    {"isbn": "9787506365437", "title": "活着", "author": "余华",
     "publisher": "作家出版社", "category": "当代文学", "price": 28.0, "stock": 3},
    {"isbn": "9787544253994", "title": "百年孤独", "author": "加西亚·马尔克斯",
     "publisher": "南海出版公司", "category": "外国文学", "price": 39.5, "stock": 3},
    {"isbn": "9787121355394", "title": "数据库系统概论", "author": "王珊",
     "publisher": "电子工业出版社", "category": "计算机", "price": 45.0, "stock": 0},
    {"isbn": "9787020024759", "title": "围城", "author": "钱锺书",
     "publisher": "人民文学出版社", "category": "当代文学", "price": 36.0, "stock": 2},
]


def seed() -> None:
    #仅当图书表为空时执行
    with Session(engine) as session:
        if session.exec(select(Book)).first():
            return

        session.add_all([Book(**item) for item in SAMPLE_BOOKS])
        session.commit()

        #借出其中一本，测试借出状态用
        target = session.exec(select(Book).where(Book.isbn == "9787536692930")).first()
        if target is not None:
            target.stock -= 1
            session.add(target)
            session.add(
                Borrow(book_id=target.id, book_title=target.title, borrower="李四")
            )
            session.commit()


if __name__ == "__main__":
    from .db import init_db

    init_db()
    seed()
    print("演示数据初始化完成")
