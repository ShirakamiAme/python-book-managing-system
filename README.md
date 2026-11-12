# 图书管理系统
Python综合实验用项目

## 技术栈

| 层次 | 技术 | 作用 |
|---|---|---|
| 数据层 | SQLite + SQLModel | 单文件数据库，模型与校验一体 |
| 接口层 | FastAPI + Uvicorn | 提供 RESTful 接口与自动文档 |
| 界面层 | Vue 3（全局构建版）+ 原生 CSS | 组件化与响应式，无需构建工具 |
| 桌面外壳 | pywebview | 把网页装进原生窗口 |
| 测试 | pytest + TestClient | 覆盖增删改查与借还流程 |

前端说明（前端部分由DeepSeek生成）：`web/vendor/vue.global.prod.js` 是 Vue 3 的全局构建版，通过 `<script>`
直接引入，**不需要 Node.js、npm 或任何打包步骤**。模板写在 `index.html` 中
`type="text/x-template"` 的 `script` 块内，由浏览器原样保留后再交给 Vue 编译，
这样 `@click`、`:class` 等指令写法不会被 HTML 解析器改写。

`web-legacy/` 保留了一版不依赖任何框架的原生 JavaScript 实现，仅作对照留档，
不参与实际运行。

配色：界面提供两套浅色主题（浅蓝 / 浅绿），通过 CSS 变量与 `data-theme`
属性整体换色，顶栏右侧的色点按钮即可切换，选择会记在 `localStorage` 中。

## 目录结构

```
.
├── app/
│   ├── config.py     全局配置（路径与常量）
│   ├── db.py         引擎与会话
│   ├── models.py     数据模型（书籍和出借记录）
│   ├── crud.py       业务逻辑
│   ├── api.py        HTTP接口
│   └── seed.py       演示数据填充
├── web/              前端（Vue3）
│   ├── index.html    页面骨架与模板
│   ├── style.css     样式
│   ├── app.js        应用逻辑
│   └── vendor/       第三方库（Vue全局构建版）
├── data/             SQLite 数据文件
├── run.py            调试接口
└── start.py          运行入口
```

## 运行

**开发调试**（只启动接口，自动重载）：

```powershell
python run.py
```

- 界面：http://127.0.0.1:8000/
- 接口文档（真的有人会看这玩意吗）：http://127.0.0.1:8000/docs

**桌面窗口**（GUI）：

```powershell
python start.py
```

## 数据库

首次启动时自动建表并写入 8 条演示数据，数据文件位于 `data/library.db`。

共设计两张表：

- `book` — 图书信息（ISBN、书名、作者、出版社、分类、定价、在库数量）
- `borrow` — 借阅记录（外键 book_id、书名快照、借阅人、借出/应还/归还日期、是否归还）

删除 `data/library.db` 后重新启动即可恢复初始演示数据。

## 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/books?kw=&page=&size=` | 分页查询，关键字匹配书名/作者/ISBN |
| GET | `/api/books/{id}` | 查询单本 |
| POST | `/api/books` | 新增（ISBN 唯一） |
| PUT | `/api/books/{id}` | 修改（部分字段） |
| DELETE | `/api/books/{id}` | 删除（有未归还记录时拒绝） |
| POST | `/api/borrows` | 借出（库存减一） |
| POST | `/api/borrows/{id}/return` | 归还（库存加一） |
| GET | `/api/borrows?unreturned=` | 借阅记录列表 |
| GET | `/api/stats` | 概览统计 |
