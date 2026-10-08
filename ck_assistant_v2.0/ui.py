import os
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QGraphicsDropShadowEffect, QFrame, 
                             QHBoxLayout, QDialog, QLineEdit, QFormLayout, 
                             QMessageBox, QSizeGrip, QComboBox, QTabWidget,
                             QFileDialog, QTextBrowser, QTextEdit, QListWidget, 
                             QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QEvent
from PyQt5.QtGui import QColor, QPainter, QPixmap, QPainterPath
from engine import load_config, save_config, DEFAULT_CONFIG, load_history, clear_history

# ================= 自定义圆角背景框 =================
class BackgroundFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_image = ""
        self.setObjectName("container")

    def set_bg_image(self, path):
        self.bg_image = path
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 20, 20)
        painter.setClipPath(path)

        if self.bg_image and os.path.exists(self.bg_image):
            pixmap = QPixmap(self.bg_image)
            if not pixmap.isNull():
                scaled_pix = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap((self.width() - scaled_pix.width()) // 2, 
                                   (self.height() - scaled_pix.height()) // 2, scaled_pix)
                painter.fillRect(rect, QColor(0, 0, 0, 200))
            else:
                painter.fillRect(rect, QColor(30, 30, 35, 245))
        else:
            painter.fillRect(rect, QColor(30, 30, 35, 245))
        painter.setPen(QColor(255, 255, 255, 25))
        painter.drawRoundedRect(rect, 20, 20)

# ================= 设置面板弹窗 =================
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 Cf 助手")
        self.setFixedSize(480, 420)
        self.setStyleSheet("background-color: #2b2b2b; color: #fff; font-size: 13px;")
        
        self.config = load_config()
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; background: #2b2b2b; }
            QTabBar::tab { background: #3a3a3a; color: #aaa; padding: 8px 16px; }
            QTabBar::tab:selected { background: #2b2b2b; color: #00E676; border-bottom: 2px solid #00E676; }
        """)
        
        cloud_tab = QWidget()
        cloud_layout = QFormLayout(cloud_tab)
        cloud_layout.setContentsMargins(15, 15, 15, 15)
        self.input_cloud_base = QLineEdit(self.config["cloud"]["base_url"])
        self.input_cloud_key = QLineEdit(self.config["cloud"]["api_key"])
        self.input_cloud_key.setEchoMode(QLineEdit.Password)
        self.input_cloud_model = QLineEdit(self.config["cloud"]["model"])
        cloud_layout.addRow("API 地址:", self.input_cloud_base)
        cloud_layout.addRow("API Key:", self.input_cloud_key)
        cloud_layout.addRow("模型名称:", self.input_cloud_model)
        tabs.addTab(cloud_tab, "云端 API")

        local_tab = QWidget()
        local_layout = QFormLayout(local_tab)
        local_layout.setContentsMargins(15, 15, 15, 15)
        self.input_local_base = QLineEdit(self.config["local"]["base_url"])
        self.input_local_key = QLineEdit(self.config["local"]["api_key"])
        self.input_local_key.setEchoMode(QLineEdit.Password)
        self.input_local_model = QLineEdit(self.config["local"]["model"])
        local_layout.addRow("本地地址:", self.input_local_base)
        local_layout.addRow("API Key:", self.input_local_key)
        local_layout.addRow("模型名称:", self.input_local_model)
        tabs.addTab(local_tab, "本地 Ollama")

        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        appearance_layout.setContentsMargins(15, 15, 15, 15)
        
        self.bg_label = QLabel(f"当前背景：{self.config.get('background_image') or '默认(无)'}")
        self.bg_label.setWordWrap(True)
        appearance_layout.addWidget(self.bg_label)
        
        btn_choose_bg = QPushButton("🖼️ 选择背景图片")
        btn_choose_bg.setStyleSheet("background: #3a3a3a; color: #fff; padding: 8px; border-radius: 5px; border: 1px solid #555;")
        btn_choose_bg.clicked.connect(self.choose_bg)
        appearance_layout.addWidget(btn_choose_bg)
        
        btn_clear_bg = QPushButton("❌ 清除背景（恢复默认深色）")
        btn_clear_bg.setStyleSheet("background: #3a3a3a; color: #FF5252; padding: 8px; border-radius: 5px; border: 1px solid #555;")
        btn_clear_bg.clicked.connect(self.clear_bg)
        appearance_layout.addWidget(btn_clear_bg)
        appearance_layout.addStretch()
        tabs.addTab(appearance_tab, "外观设置")

        layout.addWidget(tabs)
        
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("默认模型:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("云端 API", "cloud")
        self.provider_combo.addItem("本地 Ollama", "local")
        current_provider = self.config.get("provider", "cloud")
        self.provider_combo.setCurrentIndex(0 if current_provider == "cloud" else 1)
        self.provider_combo.setStyleSheet("background: #3a3a3a; color: #fff; padding: 5px; border: 1px solid #555;")
        provider_layout.addWidget(self.provider_combo)
        
        provider_layout.addWidget(QLabel("聊天模式:"))
        self.chat_mode_combo = QComboBox()
        self.chat_mode_combo.addItem("单聊(一对一)", "single")
        self.chat_mode_combo.addItem("水群模式(多人)", "group")
        current_chat_mode = self.config.get("chat_mode", "single")
        self.chat_mode_combo.setCurrentIndex(0 if current_chat_mode == "single" else 1)
        self.chat_mode_combo.setStyleSheet("background: #3a3a3a; color: #fff; padding: 5px; border: 1px solid #555;")
        provider_layout.addWidget(self.chat_mode_combo)
        
        layout.addLayout(provider_layout)
        
        btn_save = QPushButton("保存配置")
        btn_save.setStyleSheet("background-color: #00E676; color: #000; padding: 10px; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

    def choose_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择背景图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.config["background_image"] = file_path
            self.bg_label.setText(f"当前背景：{file_path}")

    def clear_bg(self):
        self.config["background_image"] = ""
        self.bg_label.setText("当前背景：默认（无）")

    def save(self):
        self.config["cloud"]["base_url"] = self.input_cloud_base.text().strip()
        self.config["cloud"]["api_key"] = self.input_cloud_key.text().strip()
        self.config["cloud"]["model"] = self.input_cloud_model.text().strip()
        self.config["local"]["base_url"] = self.input_local_base.text().strip()
        self.config["local"]["api_key"] = self.input_local_key.text().strip()
        self.config["local"]["model"] = self.input_local_model.text().strip()
        self.config["provider"] = self.provider_combo.currentData()
        self.config["chat_mode"] = self.chat_mode_combo.currentData()
        save_config(self.config)
        QMessageBox.information(self, "成功", "配置已保存！")
        self.accept()

# ================= 主界面 =================
class CfWindow(QWidget):
    update_signal = pyqtSignal(dict)
    analyze_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.update_signal.connect(self.update_data)
        self._drag_pos = None
        self.is_history_open = False
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(420, 520)
        self.resize(480, 760)
        self.setWindowTitle("Cf 聊天助手")

        main_outer_layout = QHBoxLayout(self)
        main_outer_layout.setContentsMargins(15, 15, 15, 15)
        main_outer_layout.setSpacing(10)

        self.container = BackgroundFrame()
        self.container.setStyleSheet("BackgroundFrame { background: transparent; }")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(25, 20, 25, 20)
        self.inner_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self.title_bar = QLabel("💬  Cf")
        self.title_bar.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; background: transparent;")
        
        self.chat_mode_combo = QComboBox()
        self.chat_mode_combo.addItem("单聊", "single")
        self.chat_mode_combo.addItem("水群", "group")
        self.chat_mode_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,0.08); color: #00BFFF; border: 1px solid rgba(0,150,255,0.3); border-radius: 8px; padding: 4px 8px; font-size: 12px; font-weight: bold; } QComboBox:hover { background: rgba(255,255,255,0.15); } QComboBox::drop-down { border: none; }")
        config = load_config()
        self.chat_mode_combo.setCurrentIndex(0 if config.get("chat_mode") == "single" else 1)
        self.chat_mode_combo.currentIndexChanged.connect(self.change_chat_mode)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("云端", "cloud")
        self.mode_combo.addItem("本地", "local")
        self.mode_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,0.08); color: #00E676; border: 1px solid rgba(0,200,120,0.3); border-radius: 8px; padding: 4px 8px; font-size: 12px; font-weight: bold; } QComboBox:hover { background: rgba(255,255,255,0.15); } QComboBox::drop-down { border: none; }")
        self.mode_combo.setCurrentIndex(0 if config.get("provider") == "cloud" else 1)
        self.mode_combo.currentIndexChanged.connect(self.change_provider)
        
        self.btn_history = QPushButton("📜")
        self.btn_history.setFixedSize(30, 30)
        self.btn_history.setCursor(Qt.PointingHandCursor)
        self.btn_history.setStyleSheet("QPushButton { background: transparent; border: none; color: #AAA; font-size: 16px; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 15px; }")
        self.btn_history.clicked.connect(self.toggle_history)
        
        self.btn_help = QPushButton("❓")
        self.btn_help.setFixedSize(30, 30)
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setStyleSheet("QPushButton { background: transparent; border: none; color: #AAA; font-size: 16px; font-weight: bold; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 15px; }")
        self.btn_help.clicked.connect(self.open_help)
        
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setStyleSheet("QPushButton { background: transparent; border: none; color: #AAA; font-size: 16px; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 15px; }")
        self.btn_settings.clicked.connect(self.open_settings)

        # 【新增】关闭按钮，替代右键关闭
        self.btn_close = QPushButton("✖")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("QPushButton { background: transparent; border: none; color: #AAA; font-size: 16px; font-weight: bold; } QPushButton:hover { color: #FFF; background-color: rgba(255,82,82,0.4); border-radius: 15px; }")
        self.btn_close.clicked.connect(self.close)
        
        top_bar.addWidget(self.title_bar)
        top_bar.addStretch()
        top_bar.addWidget(self.chat_mode_combo)
        top_bar.addWidget(self.mode_combo)
        top_bar.addWidget(self.btn_history)
        top_bar.addWidget(self.btn_help)
        top_bar.addWidget(self.btn_settings)
        top_bar.addWidget(self.btn_close) # 添加到顶栏右侧
        self.inner_layout.addLayout(top_bar)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255,255,255,0.08); max-height: 1px;")
        self.inner_layout.addWidget(line)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("📋 在此粘贴或输入聊天记录...\n(输入框为空时，按快捷键会直接读取剪贴板)")
        self.input_box.setFixedHeight(80)
        self.input_box.setStyleSheet("QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: #FFF; padding: 8px; font-size: 13px; font-family: 'Microsoft YaHei'; } QTextEdit:focus { border: 1px solid rgba(0, 200, 120, 0.6); }")
        self.inner_layout.addWidget(self.input_box)

        self.btn_analyze = QPushButton("🚀 开始分析")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setStyleSheet("QPushButton { background-color: rgba(0, 200, 120, 0.2); color: #00E676; border: 1px solid rgba(0, 200, 120, 0.4); border-radius: 8px; padding: 8px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: rgba(0, 200, 120, 0.35); } QPushButton:pressed { background-color: rgba(0, 200, 120, 0.5); }")
        self.btn_analyze.clicked.connect(self.analyze_requested.emit)
        self.inner_layout.addWidget(self.btn_analyze)

        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: rgba(255,255,255,0.08); max-height: 1px;")
        self.inner_layout.addWidget(line2)

        self.label_content = QLabel()
        self.label_content.setWordWrap(True)
        self.label_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_content.setStyleSheet("color: #E0E0E0; background: transparent;")
        self.label_content.setText("<div style='font-family: \"Microsoft YaHei\", sans-serif; color: #AAA; font-size: 13px; text-align: center; margin-top: 20px;'><p style='font-size: 30px; margin-bottom: 10px;'>👋</p><p style='font-size: 15px; color: #FFF; font-weight: bold;'>Cf 助手已就绪</p><p style='font-size: 12px;'>点击上方输入框粘贴内容，或直接按快捷键提取剪贴板</p></div>")
        self.inner_layout.addWidget(self.label_content)

        self.reply_buttons = []
        for i in range(6):
            btn = QPushButton()
            btn.setVisible(False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background-color: rgba(0, 200, 120, 0.1); color: #00E676; border: 1px solid rgba(0, 200, 120, 0.25); border-radius: 12px; padding: 10px 14px; font-size: 13px; text-align: left; } QPushButton:hover { background-color: rgba(0, 200, 120, 0.22); border-color: rgba(0, 200, 120, 0.5); } QPushButton:pressed { background-color: rgba(0, 200, 120, 0.4); }")
            btn.clicked.connect(lambda checked, b=btn: self._copy_reply(b))
            self.inner_layout.addWidget(btn)
            self.reply_buttons.append(btn)

        self.inner_layout.addStretch()

        bottom_bar = QHBoxLayout()
        self.hint_label = QLabel("按 Esc 关闭 | 按住窗口拖动 | 右下角拉伸")
        self.hint_label.setStyleSheet("color: #555; font-size: 10px; background: transparent;")
        bottom_bar.addWidget(self.hint_label)
        bottom_bar.addStretch()
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: rgba(0, 200, 120, 0.4); border-radius: 4px; width: 16px; height: 16px; } QSizeGrip:hover { background-color: rgba(0, 200, 120, 0.8); }")
        bottom_bar.addWidget(self.sizegrip, 0, Qt.AlignBottom | Qt.AlignRight)
        self.inner_layout.addLayout(bottom_bar)

        main_outer_layout.addWidget(self.container, stretch=1)

        self.history_panel = QFrame()
        self.history_panel.setVisible(False)
        self.history_panel.setFixedWidth(220)
        self.history_panel.setStyleSheet("QFrame { background-color: rgba(25, 25, 30, 240); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.08); }")
        
        history_layout = QVBoxLayout(self.history_panel)
        history_layout.setContentsMargins(15, 15, 15, 15)
        
        title_his = QLabel("📜 历史记录")
        title_his.setStyleSheet("color: #FFF; font-size: 14px; font-weight: bold;")
        history_layout.addWidget(title_his)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #CCC; font-size: 12px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QListWidget::item:hover { background: rgba(255,255,255,0.08); border-radius: 6px; }
            QListWidget::item:selected { background: rgba(0, 200, 120, 0.2); color: #00E676; border-radius: 6px; }
        """)
        self.history_list.itemClicked.connect(self.load_history_item)
        history_layout.addWidget(self.history_list)

        btn_clear_hist = QPushButton("🗑️ 清空历史")
        btn_clear_hist.setStyleSheet("QPushButton { background: rgba(255,82,82,0.1); color: #FF5252; border: 1px solid rgba(255,82,82,0.3); border-radius: 8px; padding: 8px; font-size: 12px; } QPushButton:hover { background: rgba(255,82,82,0.2); }")
        btn_clear_hist.clicked.connect(self.clear_all_history)
        history_layout.addWidget(btn_clear_hist)

        main_outer_layout.addWidget(self.history_panel)
        
        self.apply_background(config.get("background_image", ""))

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()
                self.raise_()
        super().changeEvent(event)

    def toggle_history(self):
        self.is_history_open = not self.is_history_open
        if self.is_history_open:
            self.history_panel.setVisible(True)
            self.setMinimumWidth(720)
            self.resize(720, self.height())
            self.refresh_history_list()
        else:
            self.history_panel.setVisible(False)
            self.setMinimumWidth(420)
            self.resize(480, self.height())

    def refresh_history_list(self):
        self.history_list.clear()
        records = load_history()
        for r in records:
            item = QListWidgetItem(f"🕒 {r['time']}\n📝 {r['input']}")
            item.setData(Qt.UserRole, r)
            self.history_list.addItem(item)

    def load_history_item(self, item):
        record = item.data(Qt.UserRole)
        if record:
            self.input_box.setText(record.get("full_input", ""))
            self.update_data(record.get("result", {}))
            self.show_status("📜 已加载历史记录")

    def clear_all_history(self):
        reply = QMessageBox.question(self, "确认", "确定要清空所有历史记录吗？此操作不可恢复。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            clear_history()
            self.refresh_history_list()
            self.show_status("🗑️ 历史记录已清空")

    def open_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cf 助手 - 帮助与排错")
        dialog.setFixedSize(520, 550)
        dialog.setStyleSheet("background-color: #2b2b2b; color: #fff; font-size: 13px;")
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("background: transparent; border: none; color: #E0E0E0; font-size: 13px; line-height: 1.6;")
        html_content = """
        <h3 style='color: #00E676;'>🚀 Cf 助手使用说明</h3>
        <p><b>🔑 核心快捷键：</b></p>
        <ul>
            <li><b>Ctrl+Shift+J</b>：优先分析输入框内容；如果输入框为空，则分析剪贴板内容</li>
            <li><b>Ctrl+Shift+S</b>：打开设置面板（配置API、换背景）</li>
            <li><b>Ctrl+Shift+Q</b>：彻底退出 Cf 助手</li>
        </ul>
        <p><b>🖱️ 界面操作：</b></p>
        <ul>
            <li><b>拖动窗口</b>：按住窗口任意空白处拖动</li>
            <li><b>调整大小</b>：拖动右下角绿色小方块</li>
            <li><b>关闭悬浮窗</b>：点击右上角 ✖ 按钮，或按 Esc 键</li>
            <li><b>复制回复</b>：点击分析结果下方的任意回复按钮</li>
        </ul>
        <hr style='border: 1px solid #444;'>
        <h3 style='color: #FF5252;'>🛠️ 常见问题排错指南</h3>
        <p><b>1. 双击 exe 没反应 / 界面闪退？</b><br>多半是被杀毒软件拦截了。请去杀毒软件的保护历史记录中，恢复并添加信任。</p>
        <p><b>2. 按了快捷键没反应？</b><br>右键点击 exe，选择“以管理员身份运行”。</p>
        <p><b>3. 一直显示“分析失败”？</b><br>云端模式：检查API Key和余额。本地模式：确保Ollama已运行，模型名称正确。</p>
        <p><b>4. 水群模式认不出谁是谁？</b><br>微信直接框选复制不会带昵称。请在微信中右键某人的发言 -> 选择“引用”，再复制对话。</p>
        <p><b>5. 为什么换了背景图，重启后没保存？</b><br>在设置面板中选好背景后，务必点击最下方的“保存配置”按钮。</p>
        """
        browser.setHtml(html_content)
        layout.addWidget(browser)
        btn_close = QPushButton("我知道了")
        btn_close.setStyleSheet("background-color: #00E676; color: #000; padding: 10px; border-radius: 6px; font-weight: bold;")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        dialog.exec_()

    def apply_background(self, img_path):
        self.container.set_bg_image(img_path)

    def change_chat_mode(self, index):
        config = load_config()
        config["chat_mode"] = self.chat_mode_combo.itemData(index)
        save_config(config)
        mode_name = "单聊（一对一）" if config["chat_mode"] == "single" else "水群模式（多人）"
        self.show_status(f"✅ 已切换至：{mode_name}")

    def change_provider(self, index):
        config = load_config()
        config["provider"] = self.mode_combo.itemData(index)
        save_config(config)
        mode_name = "云端 API" if config["provider"] == "cloud" else "本地 Ollama"
        self.show_status(f"✅ 模式已切换至：{mode_name}")

    def show_status(self, text, is_error=False):
        color = "#FF5252" if is_error else "#00E676"
        self.hint_label.setText(text)
        self.hint_label.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        QTimer.singleShot(3000, lambda: self.hint_label.setText("按 Esc 关闭 | 按住窗口拖动 | 右下角拉伸"))

    def show_error_dialog(self, msg):
        QMessageBox.critical(self, "Cf 助手出错", msg)

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            config = load_config()
            current_provider = config.get("provider", "cloud")
            current_chat_mode = config.get("chat_mode", "single")
            self.mode_combo.blockSignals(True)
            self.chat_mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(0 if current_provider == "cloud" else 1)
            self.chat_mode_combo.setCurrentIndex(0 if current_chat_mode == "single" else 1)
            self.mode_combo.blockSignals(False)
            self.chat_mode_combo.blockSignals(False)
            self.apply_background(config.get("background_image", ""))
            self.show_status("✅ 配置已保存")

    def _copy_reply(self, btn):
        QApplication.clipboard().setText(btn.property("reply_text"))
        original_text = btn.text()
        btn.setText("✅ 已复制到剪贴板！")
        QTimer.singleShot(1200, lambda: btn.setText(original_text))

    def update_data(self, data):
        surface = data.get("surface_answer", "分析中...")
        surface_probs = data.get("surface_probs", {})
        deep_intents = data.get("deep_intents", {})
        affinity = data.get("affinity_score", 50)
        danger = data.get("danger_level", 0)
        action = data.get("best_action", "无")

        surface_html = "".join([f"• {k}：{v}%" for k, v in surface_probs.items()]) if surface_probs else "• 计算中..."
        deep_html = "".join([f"• {k}：{v}%" for k, v in deep_intents.items()]) if deep_intents else "• 分析中..."

        if isinstance(affinity, (int, float)):
            a_color = "#00E676" if affinity >= 80 else ("#FFD700" if affinity >= 40 else "#FF5252")
            a_text = f"{affinity} / 100"
        else:
            a_color = "#FF69B4"
            a_text = str(affinity)

        html = f"""<div style='font-family: "Microsoft YaHei", sans-serif; font-size: 13px; line-height: 1.8;'><p style='margin: 0 0 6px 0; color: #888; font-size: 11px;'>📋 局势/表层分析</p><p style='margin: 0 0 6px 0; color: #FFF; font-weight: bold;'>{surface}</p><p style='margin: 0 0 14px 0; color: #AAA; font-size: 12px;'>{surface_html}</p><p style='margin: 0 0 6px 0; color: #888; font-size: 11px;'>🧠 真实意图</p><p style='margin: 0 0 14px 0; color: #AAA; font-size: 12px;'>{deep_html}</p><p style='margin: 0 0 6px 0; color: {a_color}; font-weight: bold;'>❤️ 好感度：{a_text}</p><p style='margin: 0 0 6px 0; color: #FFD700; font-weight: bold;'>⚠️ 危险等级：{danger} / 10</p><p style='margin: 0; color: #00BFFF;'>🎯 最佳动作：{action}</p></div>"""
        self.label_content.setText(html)

        replies = data.get("replies", [])
        for i, btn in enumerate(self.reply_buttons):
            if i < len(replies):
                r = replies[i]
                style = r.get('style', '建议')
                text = r.get('text', '')
                
                if style == "冒犯型":
                    btn.setStyleSheet("QPushButton { background-color: rgba(255, 50, 50, 0.25); color: #FF3333; border: 2px solid rgba(255, 50, 50, 0.8); border-radius: 12px; padding: 10px 14px; font-size: 13px; text-align: left; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 50, 50, 0.4); border-color: #FF3333; } QPushButton:pressed { background-color: rgba(255, 50, 50, 0.6); }")
                    btn.setText(f"💀 [终极冒犯·易被封号] {text}")
                else:
                    btn.setStyleSheet("QPushButton { background-color: rgba(0, 200, 120, 0.1); color: #00E676; border: 1px solid rgba(0, 200, 120, 0.25); border-radius: 12px; padding: 10px 14px; font-size: 13px; text-align: left; } QPushButton:hover { background-color: rgba(0, 200, 120, 0.22); border-color: rgba(0, 200, 120, 0.5); } QPushButton:pressed { background-color: rgba(0, 200, 120, 0.4); }")
                    btn.setText(f"[{style}] {text}")
                
                btn.setProperty("reply_text", text)
                btn.setVisible(True)
            else:
                btn.setVisible(False)

        self.show()
        self.activateWindow()
        self.raise_()
        self.setFocus()

    # 【核心修改】去掉右键关闭，仅保留左键拖拽
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()