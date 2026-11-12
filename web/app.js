/* ============================================================
   图书管理系统 —— 前端应用逻辑
   技术选型：Vue 3 全局构建版（vue.global.prod.js），
   通过 <script> 直接引入，无需 Node.js、npm 或任何打包工具。
   这样既保留了组件化与响应式的开发体验，又不引入前端构建链，
   与 Python 后端的部署方式天然匹配（静态文件直接由 FastAPI 托管）。

   整体采用选项式 API（Options API）：结构直观，
   与课程讲授的面向对象思想容易对应，便于在报告中说明。
   ============================================================ */

const { createApp } = Vue;

/** 后端接口统一前缀，与 FastAPI 中的路由保持一致 */
const API_BASE = "/api";

/**
 * 统一的请求封装。
 * 成功返回解析后的 JSON；失败抛出带有后端 detail 信息的 Error，
 * 由调用方统一走提示条展示，避免每处都写重复的错误处理。
 */
async function request(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `请求失败（${response.status}）`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

/** 系统是否开启了「减少动效」。开启时跳过所有额外动画。 */
function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** 生成一份空白的图书表单，新增与编辑共用 */
function blankForm() {
  return {
    id: null,
    isbn: "",
    title: "",
    author: "",
    publisher: "",
    category: "",
    price: 0,
    stock: 0,
  };
}

createApp({
  /* 模板来自 index.html 中 type="text/x-template" 的 script 块。
     这样浏览器不会预先解析模板，@click / :class 等指令写法得以原样保留。 */
  template: "#app-template",

  /* ---------------- 状态 ---------------- */
  data() {
    return {
      // 界面状态
      view: "books",            // books | borrows
      theme: "blue",            // blue（浅蓝） | green（浅绿）
      // 页签底部液块的位置与宽度（像素），由实测得出
      indicator: { left: 0, width: 0 },
      loading: false,
      saving: false,
      onlyUnreturned: false,

      // 图书列表
      books: [],
      keyword: "",
      page: 1,
      size: 10,
      total: 0,

      // 借阅记录
      borrows: [],

      // 概览统计
      stats: { total_books: 0, total_stock: 0, borrowing: 0 },

      // 图书表单弹窗
      dialog: { open: false, title: "新增图书" },
      form: blankForm(),

      // 借阅弹窗
      borrowDialog: { open: false, bookId: null, title: "", borrower: "" },

      // 提示条
      toast: { show: false, text: "", type: "info" },
      toastTimer: null,
    };
  },

  /* ---------------- 计算属性 ---------------- */
  computed: {
    /** 总页数，至少为 1，避免分页区域出现"第 1 / 0 页" */
    totalPages() {
      return Math.max(1, Math.ceil(this.total / this.size));
    },
  },

  /* ---------------- 生命周期 ---------------- */
  mounted() {
    // 恢复上次选择的配色。首屏直接应用，不播放过渡动画。
    const saved = localStorage.getItem("lib-theme");
    const initial = saved === "green" ? "green" : "blue";
    this.theme = initial;
    document.documentElement.setAttribute("data-theme", initial);

    this.loadStats();
    this.loadBooks();

    // 首屏渲染完成后测量页签位置；窗口尺寸变化时重新测量
    this.$nextTick(this.updateIndicator);
    window.addEventListener("resize", this.updateIndicator);
  },

  beforeUnmount() {
    window.removeEventListener("resize", this.updateIndicator);
  },

  /* ---------------- 方法 ---------------- */
  methods: {
    /** 顶部提示条，2.4 秒后自动消失 */
    notify(text, type = "info") {
      this.toast = { show: true, text, type };
      clearTimeout(this.toastTimer);
      this.toastTimer = setTimeout(() => {
        this.toast.show = false;
      }, 2400);
    },

    /* ---------- 配色主题 ---------- */

    /**
     * 切换配色主题。
     * 通过给 <html> 设置 data-theme 属性，由 CSS 变量整体换色，
     * 无需改动任何 DOM 结构与样式类名。
     * 若确实发生了切换，顺带播放一次顶栏的液态过渡。
     */
    setTheme(name) {
      const changed = this.theme !== name;
      this.theme = name;
      document.documentElement.setAttribute("data-theme", name);
      try {
        localStorage.setItem("lib-theme", name);
      } catch {
        // 隐私模式下 localStorage 可能写入失败，忽略即可
      }
      if (changed) this.pulseLiquid();
    },

    /**
     * 顶栏的液态搅动：玻璃整层放大、模糊加重再回弹，同时反光扫过一次。
     *
     * 这里用 Web Animations API 而不是切 CSS 类，原因是类切换依赖 Vue 的
     * 异步渲染：先置 false 再置 true 会被合并到同一帧，连续快速操作时
     * 动画不会重播。el.animate() 每次调用都是独立的一次播放，没有这个问题。
     */
    pulseLiquid() {
      if (prefersReducedMotion()) return;

      const glass = this.$el.querySelector(".liquid-glass");
      const sheen = this.$el.querySelector(".sheen");

      if (glass && typeof glass.animate === "function") {
        glass.animate(
          [
            { transform: "scale(1) translateY(0)", filter: "blur(26px) saturate(150%)" },
            {
              transform: "scale(1.08) translateY(-5px)",
              filter: "blur(36px) saturate(230%)",
              offset: 0.45,
            },
            { transform: "scale(1) translateY(0)", filter: "blur(26px) saturate(150%)" },
          ],
          { duration: 800, easing: "cubic-bezier(.34, 1.2, .4, 1)" }
        );
      }

      if (sheen && typeof sheen.animate === "function") {
        sheen.animate(
          [
            { transform: "translateX(-100%)", opacity: 0 },
            { opacity: 0.95, offset: 0.3 },
            { transform: "translateX(100%)", opacity: 0 },
          ],
          { duration: 800, easing: "ease" }
        );
      }
    },

    /**
     * 两个视图互切时的横扫光层。
     * 一层柔和的液色从左流到右，盖住内容交换的那一瞬。
     */
    runSweep() {
      if (prefersReducedMotion()) return;

      const sweep = this.$el.querySelector(".liquid-sweep");
      if (!sweep || typeof sweep.animate !== "function") return;

      sweep.animate(
        [
          { transform: "translateX(-70%)", opacity: 0 },
          { transform: "translateX(-15%)", opacity: 0.9, offset: 0.28 },
          { transform: "translateX(70%)", opacity: 0 },
        ],
        { duration: 620, easing: "cubic-bezier(.4, 0, .2, 1)" }
      );
    },

    /** 测量当前选中页签的位置与宽度，驱动底部液块滑动过去 */
    updateIndicator() {
      const active = this.$el.querySelector(".tab.active");
      if (!active) return;
      this.indicator = {
        left: active.offsetLeft,
        width: active.offsetWidth,
      };
    },

    /* ---------- 统计 ---------- */

    async loadStats() {
      try {
        this.stats = await request("/stats");
      } catch (error) {
        // 统计失败不影响主流程，静默处理
        console.error("统计加载失败：", error);
      }
    },

    /* ---------- 图书查询 ---------- */

    async loadBooks() {
      this.loading = true;
      try {
        const query = new URLSearchParams({
          kw: this.keyword,
          page: String(this.page),
          size: String(this.size),
        });
        const data = await request(`/books?${query.toString()}`);
        this.books = data.items;
        this.total = data.total;
      } catch (error) {
        this.notify(error.message, "error");
      } finally {
        this.loading = false;
      }
    },

    searchBooks() {
      this.page = 1;
      this.loadBooks();
    },

    resetSearch() {
      this.keyword = "";
      this.page = 1;
      this.loadBooks();
    },

    goPage(target) {
      if (target < 1 || target > this.totalPages) return;
      this.page = target;
      this.loadBooks();
    },

    /* ---------- 图书新增与编辑 ---------- */

    openCreate() {
      this.form = blankForm();
      this.dialog = { open: true, title: "新增图书" };
    },

    openEdit(book) {
      this.form = { ...blankForm(), ...book };
      this.dialog = { open: true, title: "编辑图书" };
    },

    closeDialog() {
      this.dialog.open = false;
    },

    async submitForm() {
      if (!this.form.isbn || !this.form.title) {
        this.notify("ISBN 与书名不能为空", "error");
        return;
      }

      this.saving = true;
      const bookId = this.form.id;
      const payload = {
        isbn: this.form.isbn,
        title: this.form.title,
        author: this.form.author,
        publisher: this.form.publisher,
        category: this.form.category,
        price: Number(this.form.price) || 0,
        stock: Math.max(0, parseInt(this.form.stock, 10) || 0),
      };

      try {
        if (bookId) {
          await request(`/books/${bookId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
          this.notify("修改成功", "success");
        } else {
          await request("/books", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          this.notify("新增成功", "success");
        }
        this.closeDialog();
        this.loadBooks();
        this.loadStats();
      } catch (error) {
        this.notify(error.message, "error");
      } finally {
        this.saving = false;
      }
    },

    async removeBook(book) {
      if (!window.confirm(`确认删除《${book.title}》？删除后不可恢复。`)) return;
      try {
        await request(`/books/${book.id}`, { method: "DELETE" });
        this.notify("删除成功", "success");
        this.loadBooks();
        this.loadStats();
      } catch (error) {
        this.notify(error.message, "error");
      }
    },

    /* ---------- 借阅与归还 ---------- */

    openBorrow(book) {
      if (book.stock <= 0) {
        this.notify(`《${book.title}》暂无在库副本`, "error");
        return;
      }
      this.borrowDialog = {
        open: true,
        bookId: book.id,
        title: book.title,
        borrower: "",
      };
    },

    closeBorrowDialog() {
      this.borrowDialog.open = false;
    },

    async submitBorrow() {
      if (!this.borrowDialog.borrower) {
        this.notify("请输入借阅人姓名", "error");
        return;
      }

      this.saving = true;
      try {
        await request("/borrows", {
          method: "POST",
          body: JSON.stringify({
            book_id: this.borrowDialog.bookId,
            borrower: this.borrowDialog.borrower,
          }),
        });
        this.notify("借出成功", "success");
        this.closeBorrowDialog();
        this.loadBooks();
        this.loadStats();
      } catch (error) {
        this.notify(error.message, "error");
      } finally {
        this.saving = false;
      }
    },

    async loadBorrows() {
      try {
        const data = await request(`/borrows?unreturned=${this.onlyUnreturned}`);
        this.borrows = data.items;
      } catch (error) {
        this.notify(error.message, "error");
      }
    },

    async returnBook(record) {
      try {
        await request(`/borrows/${record.id}/return`, { method: "POST" });
        this.notify("归还成功", "success");
        this.loadBorrows();
        this.loadStats();
      } catch (error) {
        this.notify(error.message, "error");
      }
    },

    /* ---------- 视图切换 ---------- */

    switchView(target) {
      if (this.view === target) return;

      this.view = target;
      this.runSweep();

      // 页签激活态已变，重新测量液块应该滑到哪里
      this.$nextTick(this.updateIndicator);

      if (target === "borrows") {
        this.loadBorrows();
      } else {
        this.loadBooks();
      }
    },
  },
}).mount("#app");
