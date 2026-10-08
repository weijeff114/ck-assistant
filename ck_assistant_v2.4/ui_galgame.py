import os
import sys
import base64
import threading
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QTextEdit, QComboBox, 
                             QDialog, QListWidget, QListWidgetItem, QMessageBox, 
                             QLineEdit, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPainter, QPixmap, QPainterPath, QLinearGradient, QFont
from engine import (load_config, save_config, analyze_chat, load_history, 
                    clear_history, clear_context, load_saves, create_save, 
                    delete_save, clear_saves)

# ================= 存档面板 =================
class SavesDialog(QDialog):
    def __init__(self, session_name, parent=None):
        super().__init__(parent)
        self.session_name = session_name
        self.parent_window = parent
        self.setWindowTitle(f"📖 剧情存档 - {session_name}")
        self.setFixedSize(500, 400)
        self.setStyleSheet("background-color: #1a1a2e; color: #fff; font-size: 13px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,126,182,0.3); color: #fff; border-radius: 8px; padding: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); border-radius: 6px; }
            QListWidget::item:hover { background: rgba(255,126,182,0.1); }
            QListWidget::item:selected { background: rgba(255,126,182,0.3); color: #fff; }
        """)
        self.list_widget.itemDoubleClicked.connect(self.load_save)
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton("🗑️ 清空全部存档")
        btn_clear.setStyleSheet("background: rgba(255,82,82,0.1); border: 1px solid #FF5252; color: #FF5252; padding: 8px; border-radius: 6px;")
        btn_clear.clicked.connect(self.clear_all)
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("background: #333; color: #fff; padding: 8px; border-radius: 6px;")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self.refresh_saves()

    def refresh_saves(self):
        self.list_widget.clear()
        saves = load_saves(self.session_name)
        if not saves:
            self.list_widget.addItem("暂无存档，去玩一玩再回来保存吧～")
            return
        for s in saves:
            item = QListWidgetItem(f"💠 {s['note']}\n🕒 {s['time']} · 好感度 {s['scene'].get('affinity', 50)} · 危险度 {s['scene'].get('danger', 0)}")
            item.setData(Qt.UserRole, s['id'])
            self.list_widget.addItem(item)

    def load_save(self, item):
        save_id = item.data(Qt.UserRole)
        if not save_id: return
        self.accept()
        if self.parent_window:
            self.parent_window.load_save_data(save_id)

    def clear_all(self):
        if QMessageBox.question(self, "确认", "确定清空所有存档吗？", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            clear_saves(self.session_name)
            self.refresh_saves()

# ================= 主界面 =================
class GalgameWindow(QWidget):
    analysis_done = pyqtSignal(dict, str)
    analysis_started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_scene = None
        self.analysis_done.connect(self.render_scene)
        self.analysis_started.connect(self.on_analysis_started)
        self.initUI()
        self.load_sessions()

    def initUI(self):
        self.setWindowTitle("Cf · Galgame 桌面版 v2.4")
        self.setMinimumSize(600, 800)
        self.setStyleSheet("""
            QWidget { background-color: #0a0a12; color: #e8e8f0; font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; }
            QLabel { background: transparent; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # ===== 1. 顶栏 =====
        topbar = QHBoxLayout()
        title = QLabel("✦ Cf · Galgame v2.4")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff7eb6; background: transparent;")
        
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("""
            QComboBox { background: rgba(0,0,0,0.4); color: #7be3ff; border: 1px solid rgba(123,227,255,0.3); border-radius: 8px; padding: 6px 15px; font-weight: bold; font-size: 12px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #1a1a2e; color: #fff; selection-background-color: #ff7eb6; }
        """)
        self.session_combo.currentTextChanged.connect(self.change_session)
        
        btn_saves = QPushButton("💾 存档")
        btn_saves.setStyleSheet("""
            QPushButton { background: rgba(255,126,182,0.15); border: 1px solid rgba(255,126,182,0.4); color: #ff7eb6; border-radius: 8px; padding: 6px 15px; font-weight: bold; }
            QPushButton:hover { background: rgba(255,126,182,0.3); }
        """)
        btn_saves.clicked.connect(self.open_saves)
        
        topbar.addWidget(title)
        topbar.addStretch()
        topbar.addWidget(QLabel("当前会话:"))
        topbar.addWidget(self.session_combo)
        topbar.addWidget(btn_saves)
        layout.addLayout(topbar)

        # ===== 2. 角色气泡区 =====
        self.scene_frame = QFrame()
        self.scene_frame.setStyleSheet("""
            QFrame { background: rgba(22, 22, 34, 0.85); border: 1px solid rgba(123,227,255,0.15); border-radius: 20px; }
        """)
        scene_layout = QVBoxLayout(self.scene_frame)
        scene_layout.setContentsMargins(25, 25, 25, 25)
        scene_layout.setSpacing(15)
        
        self.character_tag = QLabel("对 方")
        self.character_tag.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7eb6, stop:1 #b388ff);
            color: #0a0a12; font-weight: bold; font-size: 12px; padding: 5px 15px; border-radius: 15px;
            letter-spacing: 1px;
        """)
        self.character_tag.setFixedSize(80, 28)
        
        self.dialogue_text = QLabel("「等待你的第一条情报...」")
        self.dialogue_text.setWordWrap(True)
        self.dialogue_text.setStyleSheet("""
            font-size: 17px; line-height: 1.7; color: #fff; padding: 15px 20px; 
            background: rgba(0,0,0,0.3); border-left: 3px solid #ff7eb6; border-radius: 8px;
        """)
        
        scene_layout.addWidget(self.character_tag)
        scene_layout.addWidget(self.dialogue_text)
        layout.addWidget(self.scene_frame)

        # ===== 3. 状态栏 =====
        status_layout = QHBoxLayout()
        self.affinity_label = QLabel("❤️ 好感度: --")
        self.affinity_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff7eb6;")
        self.danger_label = QLabel("⚠️ 危险度: --")
        self.danger_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffb84d;")
        
        status_layout.addWidget(self.affinity_label)
        status_layout.addStretch()
        status_layout.addWidget(self.danger_label)
        layout.addLayout(status_layout)

        # ===== 4. 行动建议 =====
        self.advice_label = QLabel("")
        self.advice_label.setWordWrap(True)
        self.advice_label.setVisible(False)
        self.advice_label.setStyleSheet("""
            background: rgba(179,136,255,0.15); border: 1px solid rgba(179,136,255,0.3); 
            color: #d0c0ff; padding: 12px 15px; border-radius: 12px; font-size: 13px; line-height: 1.5;
        """)
        layout.addWidget(self.advice_label)

        # ===== 5. 回复选项按钮区 =====
        self.choices_layout = QVBoxLayout()
        self.choices_layout.setSpacing(10)
        layout.addLayout(self.choices_layout)

        # ===== 6. 输入区 =====
        input_frame = QFrame()
        input_frame.setStyleSheet("background: rgba(22, 22, 34, 0.85); border-radius: 16px; padding: 15px;")
        input_layout = QVBoxLayout(input_frame)
        
        # v2.4 心情与背景
        mood_layout = QHBoxLayout()
        self.mood_combo = QComboBox()
        self.mood_combo.setEditable(True)
        self.mood_combo.addItems(["平静", "开心", "烦躁", "委屈", "高冷", "发疯"])
        self.mood_combo.setStyleSheet("QComboBox { background: rgba(0,0,0,0.4); color: #FFD700; border: 1px solid rgba(255,215,0,0.3); border-radius: 6px; padding: 4px 10px; font-size: 12px; }")
        btn_bg = QPushButton("📖 前情提要")
        btn_bg.setStyleSheet("background: rgba(0,191,255,0.1); border: 1px solid rgba(0,191,255,0.3); color: #00BFFF; font-size: 12px; border-radius: 6px; padding: 5px 10px;")
        btn_bg.clicked.connect(self.edit_background)
        
        mood_layout.addWidget(QLabel("🎭 心情:"))
        mood_layout.addWidget(self.mood_combo, stretch=1)
        mood_layout.addWidget(btn_bg)
        input_layout.addLayout(mood_layout)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("粘贴对方的聊天记录，开启这场「对话」...")
        self.input_box.setFixedHeight(90)
        self.input_box.setStyleSheet("QTextEdit { background: rgba(0,0,0,0.4); border: 1px solid #333; border-radius: 8px; color: #fff; padding: 10px; font-size: 14px; } QTextEdit:focus { border-color: #ff7eb6; }")
        input_layout.addWidget(self.input_box)

        self.btn_analyze = QPushButton("⚔️ 开启分析")
        self.btn_analyze.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7eb6, stop:1 #b388ff); color: #0a0a12; font-size: 15px; font-weight: bold; padding: 12px; border-radius: 10px; }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:disabled { opacity: 0.5; }
        """)
        self.btn_analyze.clicked.connect(self.analyze)
        input_layout.addWidget(self.btn_analyze)

        layout.addWidget(input_frame)

    # ================= 逻辑处理 =================
    def load_sessions(self):
        config = load_config()
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        for s in config.get("sessions", ["默认单聊"]):
            self.session_combo.addItem(s)
        self.session_combo.setCurrentText(config.get("current_session", "默认单聊"))
        self.session_combo.blockSignals(False)
        self.change_session(self.session_combo.currentText())

    def change_session(self, session_name):
        if not session_name: return
        config = load_config()
        config["current_session"] = session_name
        save_config(config)
        
        self.dialogue_text.setText(f"「已切换至【{session_name}】，请粘贴新的情报...」")
        self.affinity_label.setText("❤️ 好感度: --")
        self.danger_label.setText("⚠️ 危险度: --")
        self.advice_label.setVisible(False)
        self.clear_choices()
        self.current_scene = None

    def clear_choices(self):
        while self.choices_layout.count():
            item = self.choices_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

    def edit_background(self):
        session_name = self.session_combo.currentText()
        config = load_config()
        current_bg = config.get("session_backgrounds", {}).get(session_name, "")
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑【{session_name}】的前情提要")
        dialog.setFixedSize(450, 300)
        dialog.setStyleSheet("background-color: #1a1a2e; color: #fff;")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("简述之前发生过的相关事件："))
        bg_input = QTextEdit()
        bg_input.setPlainText(current_bg)
        bg_input.setPlaceholderText("例如：昨天她过生日，我因为加班忘记买礼物了...")
        bg_input.setStyleSheet("background: rgba(0,0,0,0.3); border: 1px solid #444; color: #fff; padding: 10px; border-radius: 8px;")
        layout.addWidget(bg_input)
        
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet("background: #ff7eb6; color: #000; font-weight: bold; padding: 10px; border-radius: 8px;")
        
        def save_bg():
            config.setdefault("session_backgrounds", {})[session_name] = bg_input.toPlainText().strip()
            save_config(config)
            dialog.accept()
            QMessageBox.information(self, "成功", "前情提要已保存！")
            
        btn_save.clicked.connect(save_bg)
        layout.addWidget(btn_save)
        dialog.exec_()

    def open_saves(self):
        dialog = SavesDialog(self.session_combo.currentText(), self)
        dialog.exec_()

    def load_save_data(self, save_id):
        saves = load_saves(self.session_combo.currentText())
        save = next((s for s in saves if s['id'] == save_id), None)
        if not save: return
        
        scene = save['scene']
        self.dialogue_text.setText(f"「{scene.get('dialogue', '')}」")
        self.affinity_label.setText(f"❤️ 好感度: {scene.get('affinity', 50)} / 100")
        self.danger_label.setText(f"⚠️ 危险度: {scene.get('danger', 0)} / 10")
        self.input_box.setPlainText(scene.get('original_input', ''))
        
        if scene.get('advice'):
            self.advice_label.setText(f"💡 行动建议：{scene['advice']}")
            self.advice_label.setVisible(True)
        else:
            self.advice_label.setVisible(False)
            
        self.clear_choices()
        self.render_choices(scene.get('replies', []))
        self.current_scene = scene

    def on_analysis_started(self):
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("⏳ 正在推演剧情...")
        self.dialogue_text.setText("「对方正在思考中...」")
        self.clear_choices()
        self.advice_label.setVisible(False)

    def analyze(self):
        chat_text = self.input_box.toPlainText().strip()
        if not chat_text:
            QMessageBox.warning(self, "提示", "请先粘贴聊天记录！")
            return
            
        self.analysis_started.emit()
        
        session_name = self.session_combo.currentText()
        user_mood = self.mood_combo.currentText().strip()
        config = load_config()
        user_context = config.get("session_backgrounds", {}).get(session_name, "")
        
        def run():
            try:
                # v2.4 核心：传入心情和前情提要
                result = analyze_chat(chat_text, session_name, image_base64=None, user_mood=user_mood, user_context=user_context)
                self.analysis_done.emit(result, chat_text)
            except Exception as e:
                self.analysis_done.emit({"surface_answer": f"分析失败：{str(e)}", "replies": []}, chat_text)

        threading.Thread(target=run).start()

    def render_scene(self, data, chat_text):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("⚔️ 开启分析")
        
        lines = chat_text.split('\n')
        last_line = lines[-1] if lines else chat_text
        display_text = last_line.replace("对方说：", "").strip()
        if not display_text: display_text = data.get("surface_answer", "分析失败")
        
        self.dialogue_text.setText(f"「{display_text}」")
        
        affinity = data.get("affinity_score", 50)
        danger = data.get("danger_level", 0)
        self.affinity_label.setText(f"❤️ 好感度: {affinity} / 100")
        self.danger_label.setText(f"⚠️ 危险度: {danger} / 10")
        
        advice = data.get("action_advice", "")
        if advice and advice != "无":
            self.advice_label.setText(f"💡 行动建议：{advice}")
            self.advice_label.setVisible(True)
            
        replies = data.get("replies", [])
        self.render_choices(replies)
        
        self.current_scene = {
            "dialogue": display_text, "affinity": affinity, "danger": danger,
            "advice": advice, "replies": replies, "original_input": chat_text
        }
        
        # 提示保存
        QTimer.singleShot(500, lambda: self.prompt_save())

    def render_choices(self, replies):
        self.clear_choices()
        for r in replies:
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            
            style = r.get('style', '建议')
            text = r.get('text', '')
            prediction = r.get('prediction', '')
            
            color = "#00E676"; border = "rgba(0,200,120,0.3)"; bg = "rgba(0,200,120,0.1)"
            if style == "幽默型": color, border, bg = "#7be3ff", "rgba(123,227,255,0.3)", "rgba(123,227,255,0.1)"
            elif style == "高冷型": color, border, bg = "#b0b0c0", "rgba(138,138,160,0.3)", "rgba(138,138,160,0.1)"
            elif style in ["发疯型", "更疯型"]: color, border, bg = "#CE93D8", "rgba(179,136,255,0.4)", "rgba(179,136,255,0.1)"
            elif style == "冒犯型": color, border, bg = "#FF5252", "rgba(255,82,82,0.6)", "rgba(255,82,82,0.15)"
            
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: {bg}; border: 2px solid {border}; color: {color}; 
                    border-radius: 14px; padding: 15px 20px; text-align: left; font-size: 13px; 
                }}
                QPushButton:hover {{ background: {bg.replace('0.1', '0.25') if '0.1' in bg else bg.replace('0.15', '0.3')}; border-color: {color}; }}
            """)
            
            display_text = f"[{style}] {text}"
            if prediction: display_text += f"\n⤷ 预测对方：{prediction}"
                
            btn.setText(display_text)
            btn.clicked.connect(lambda checked, t=text, b=btn: self.copy_reply(t, b))
            self.choices_layout.addWidget(btn)

    def copy_reply(self, text, btn):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        original = btn.text()
        btn.setText("✅ 已复制到剪贴板")
        QTimer.singleShot(1000, lambda: btn.setText(original))

    def prompt_save(self):
        if not self.current_scene: return
        reply = QMessageBox.question(self, "保存剧情", "是否将当前剧情保存到存档？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            note, ok = QInputDialog.getText(self, "保存存档", "给这个剧情节点起个名字：")
            if ok and note.strip():
                create_save(self.session_combo.currentText(), note.strip(), self.current_scene)
                QMessageBox.information(self, "成功", "剧情已保存！")