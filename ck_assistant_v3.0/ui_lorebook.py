# =========================================================
# 世界书管理弹窗 LorebookDialog（多世界书/知识包系统）
# 数据存储于 config.json：
#   lorebooks:            { 书名: {description, blacklist, terms, last_updated} }
#   session_lorebooks:    { 会话名: [启用书名...] }
# =========================================================
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget, QSplitter, QFormLayout
)
from PyQt5.QtCore import Qt

from engine_config import load_config, save_config
import engine


class LorebookDialog(QDialog):
    """世界书管理弹窗：浏览、新建、编辑、删除、启用世界书（知识包）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_book = None
        self.setWindowTitle("多世界书管理 - 知识包")
        self.setMinimumSize(720, 520)
        self.setStyleSheet(
            "QDialog { background-color: #1e1e28; }"
            "QLabel { color: #e0e0e0; font-size: 13px; }"
            "QLineEdit, QTextEdit, QListWidget, QTableWidget {"
            "  background: #2a2a36; color: #f0f0f0;"
            "  border: 1px solid #3a3a48; border-radius: 6px; padding: 6px; }"
            "QPushButton { background: #00c853; color: #111;"
            "  border-radius: 6px; padding: 6px 12px; font-weight: bold; }"
            "QPushButton:hover { background: #00e676; }"
            "QPushButton.btn-danger { background: #d32f2f; color: #fff; }"
            "QPushButton:hover { background: #d32f2f; }"
            "QPushButton.btn-plain { background: #3a3a48; color: #e0e0e0; }"
            "QPushButton.btn-plain:hover { background: #4a4a5a; }"
        )
        self._load_config()
        self._build_ui()
        self.refresh_list()
        self.refresh_apply_list()

    # ---------- 数据读写 ----------
    def _load_config(self):
        cfg = load_config()
        if not isinstance(cfg, dict):
            cfg = {}
        cfg.setdefault("lorebooks", {})
        cfg.setdefault("session_lorebooks", {})
        return cfg

    def _save(self, cfg):
        try:
            save_config(cfg)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存配置：{e}")

    def _build_ui(self):
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入或修改书名")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("核心机制 / 世界背景描述…")
        self.black_input = QTextEdit()
        self.black_input.setPlaceholderText("雷区 / 禁忌 / 不能做的事…")
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("输入会话名（如：默认单聊）")

        self.term_table = QTableWidget(0, 2)
        self.term_table.setHorizontalHeaderLabels(["黑话", "解释"])

        form = QFormLayout()
        form.addRow("书名", self.name_input)
        form.addRow("核心机制", self.desc_input)
        form.addRow("雷区", self.black_input)

        box = QVBoxLayout(self)

        # [第三阶段] AI自动写书 + 联网查梗 工作台
        ai_bar = QHBoxLayout()
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("输入主题，如：明日方舟")
        ai_bar.addWidget(self.topic_input, stretch=3)
        btn_ai = QPushButton("AI自动写书")
        btn_ai.setObjectName("primary")
        btn_ai.clicked.connect(self.on_auto_write)
        ai_bar.addWidget(btn_ai)
        self.mode_query = QLineEdit()
        self.mode_query.setPlaceholderText("输入想查的梗词")
        ai_bar.addWidget(self.mode_query, stretch=3)
        btn_meme = QPushButton("联网查梗")
        btn_meme.setObjectName("primary")
        btn_meme.clicked.connect(self.on_web_meme)
        ai_bar.addWidget(btn_meme)
        box.addLayout(ai_bar)
        self.mode_output = QTextEdit()
        self.mode_output.setReadOnly(True)
        self.mode_output.setPlaceholderText("AI自动写书 / 联网查梗 的结果会显示在这里…")
        self.mode_output.setMaximumHeight(120)
        box.addWidget(self.mode_output)

        box.addLayout(form)
        box.addWidget(QLabel("会话与启用"))
        box.addWidget(self.session_input)
        box.addWidget(self.term_table)
        self.term_table.setMinimumHeight(160)

        btns = QHBoxLayout()
        for text, slot in (
            ("添加黑话", self.add_term),
            ("删除黑话", self.del_term),
            ("新建书", self.new_book),
            ("保存当前", self.save_current),
            ("删除书", self.delete_book),
            ("启用会话", self.apply_session),
            ("刷新列表", self.refresh_list),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        box.addLayout(btns)
        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        box.addWidget(self.btn_ok)

    def add_term(self):
        row = self.term_table.rowCount()
        self.term_table.insertRow(row)
        self.term_table.setItem(row, 0, QTableWidgetItem(""))
        self.term_table.setItem(row, 1, QTableWidgetItem(""))

    def del_term(self):
        rows = sorted({r.row() for r in self.term_table.selectedItems()}, reverse=True)
        for r in rows:
            self.term_table.removeRow(r)

    def _collect_terms(self):
        terms = {}
        for r in range(self.term_table.rowCount()):
            k = self.term_table.item(r, 0)
            v = self.term_table.item(r, 1)
            key = k.text().strip() if k else ""
            val = v.text().strip() if v else ""
            if key:
                terms[key] = val
        return terms

    def refresh_list(self):
        """重建书架列表（最简单实现：无对话框，仅打印书名供测试）。"""
        names = sorted(self._load_config().get("lorebooks", {}).keys())
        print("当前世界书:", ", ".join(names) if names else "(无)")

    def new_book(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "未命名", "请先输入书名。")
            return
        cfg = self._load_config()
        cfg.setdefault("lorebooks", {})
        if name in cfg["lorebooks"]:
            QMessageBox.warning(self, "重复", f"《{name}》已存在。")
            return
        cfg["lorebooks"][name] = {"description": self.desc_input.toPlainText(),
                                  "terms": self._collect_terms(),
                                  "last_updated": ""}
        self._save(cfg)
        self.refresh_list()

    def save_current(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "未命名", "请先输入书名。")
            return
        cfg = self._load_config()
        cfg.setdefault("lorebooks", {})
        cfg["lorebooks"][name] = {"description": self.desc_input.toPlainText(),
                                  "terms": self._collect_terms(),
                                  "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        self._save(cfg)
        from engine_config import load_config as __lc
        __c = __lc()
        sl = __c.setdefault("session_lorebooks", {}).setdefault(self.session_input.text().strip() or "默认单聊", [])
        if name not in sl:
            sl.append(name)
        self._save(__c)
        self.refresh_list()
        QMessageBox.information(self, "已保存", f"《{name}》保存成功。")

    def delete_book(self):
        self.refresh_list()

    def apply_session(self):
        cfg = self._load_config()
        sel = cfg.setdefault("session_lorebooks", {}).setdefault(
            self.session_input.text().strip() or "默认单聊", [])
        print("本会话启用:", ", ".join(sel) if sel else "(无)")

    def selected_names(self):
        cfg = self._load_config()
        return cfg.get("session_lorebooks", {}).get(
            self.session_input.text().strip() or "默认单聊", [])

    def on_auto_write(self):
        topic = (self.topic_input.text() or "").strip()
        if not topic:
            QMessageBox.warning(self, "提示", "请先输入主题，如：明日方舟")
            return
        try:
            ret = engine.auto_write_lorebook_from_topic(topic)
        except Exception as ex:
            self.mode_output.setPlainText("AI 自动写书失败：" + str(ex))
            return
        self.refresh_list()
        self.mode_output.setPlainText(
            "已生成世界书《%s》（含 %d 个词条）"
            % (ret.get("name", "未命名"), len(ret.get("terms", {}) or {}))
        )

    def on_web_meme(self):
        word = (self.mode_query.text() or "").strip()
        if not word:
            QMessageBox.warning(self, "提示", "请输入要查的梗词")
            return
        self.mode_output.setPlainText("正在联网查询 “" + word + "” …")
        import threading
        def _task():
            try:
                res = engine.web_search(word, max_results=5)
            except Exception as ex:
                res = [{"title": "查询异常", "body": str(ex), "href": ""}]
            if not isinstance(res, list):
                res = []
            lines = ["%d. %s\n%s\n%s" % (i + 1, r.get("title", ""), r.get("body", ""), r.get("href", ""))
                     for i, r in enumerate(res[:5])]
            self.mode_output.setPlainText("\n\n".join(lines) if lines else "没有搜到相关内容")
        threading.Thread(target=_task, daemon=True).start()


def lorebook_prompt_for(book_name="默认", max_terms=20):
    cfg = load_config()
    books = cfg.get("lorebooks", {}) if isinstance(cfg, dict) else {}
    data = books.get(book_name)
    if not data:
        return ""
    parts = []
    desc = (data.get("description") or "").strip()
    if desc:
        parts.append("【世界背景/核心机制】" + desc)
    black = (data.get("blacklist") or "").strip()
    if black:
        parts.append("【雷区/禁忌】" + black)
    terms = data.get("terms", {}) or {}
    term_lines = [f"- {k}: {v}" for k, v in list(terms.items())[:max_terms]]
    if term_lines:
        parts.append("【黑话速查】\n" + "\n".join(term_lines))
    return "\n".join(parts) + "\n"
