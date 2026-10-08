import os
import sys
import base64
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QGraphicsDropShadowEffect, QFrame, 
                             QHBoxLayout, QDialog, QLineEdit, QFormLayout, 
                             QMessageBox, QSizeGrip, QComboBox, QTabWidget,
                             QFileDialog, QTextBrowser, QTextEdit, QListWidget, 
                             QListWidgetItem, QSlider, QInputDialog, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QEvent
from PyQt5.QtGui import QColor, QPainter, QPixmap, QPainterPath, QImage, QLinearGradient, QIcon, QFont
from engine import (load_config, save_config, DEFAULT_CONFIG, load_history, 
                    clear_history, clear_context, extract_style_from_sample)

# ================= 自定义毛玻璃圆角背景框 =================
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
        path.addRoundedRect(rect, 24, 24)
        painter.setClipPath(path)
        if self.bg_image and os.path.exists(self.bg_image):
            pixmap = QPixmap(self.bg_image)
            if not pixmap.isNull():
                scaled_pix = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap((self.width() - scaled_pix.width()) // 2, (self.height() - scaled_pix.height()) // 2, scaled_pix)
                painter.fillRect(rect, QColor(15, 15, 20, 210))
            else: self.draw_gradient(painter, rect)
        else: self.draw_gradient(painter, rect)
        painter.setPen(QColor(0, 200, 120, 40))
        painter.drawRoundedRect(rect, 24, 24)
    def draw_gradient(self, painter, rect):
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(28, 28, 38, 250))
        gradient.setColorAt(1, QColor(18, 18, 24, 250))
        painter.fillRect(rect, gradient)

# ================= 快捷人物设定弹窗 =================
class ProfileDialog(QDialog):
    def __init__(self, session_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"设定对象：{session_name}")
        self.setFixedSize(400, 200)
        self.setStyleSheet("background-color: #1e1e24; color: #fff; font-size: 13px; border-radius: 10px;")
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("请简述这个人是谁，以及你们的关系："))
        self.profile_input = QTextEdit()
        self.profile_input.setPlaceholderText("例如：女，25岁，女朋友，最近在减肥，情绪敏感；\n或者：男，45岁，直属领导，严肃古板，看重结果。")
        
        config = load_config()
        current_profile = config.get("session_profiles", {}).get(session_name, "")
        self.profile_input.setText(current_profile)
        self.profile_input.setStyleSheet("QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #FFF; padding: 8px; }")
        layout.addWidget(self.profile_input)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet("background: #00E676; color: #000; padding: 8px; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.save_profile)
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("background: #333; color: #fff; padding: 8px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
    def save_profile(self):
        self.accept()

# ================= 设置面板弹窗 =================
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cf 助手 v2.3 设置")
        self.setFixedSize(600, 700)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: #e0e0e0; font-size: 13px; }
            QLabel { color: #aaa; }
            QLineEdit, QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; padding: 6px; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #00E676; }
        """)
        self.config = load_config()
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #26262e; border-radius: 8px; }
            QTabBar::tab { background: #1e1e24; color: #888; padding: 10px 18px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #26262e; color: #00E676; border-bottom: 2px solid #00E676; }
            QTabBar::tab:hover { background: #2a2a33; }
        """)
        
        provider_tab = QWidget()
        provider_layout = QHBoxLayout(provider_tab)
        provider_layout.setContentsMargins(15, 15, 15, 15)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("已保存的 API 配置："))
        self.provider_list = QListWidget()
        self.provider_list.setStyleSheet("QListWidget { background: rgba(255,255,255,0.02); border: 1px solid #333; color: #fff; } QListWidget::item { padding: 10px; } QListWidget::item:selected { background: #00E676; color: #000; }")
        self.provider_list.itemClicked.connect(self.on_provider_selected)
        left_layout.addWidget(self.provider_list)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ 新增")
        btn_add.setStyleSheet("background: #3a3a3a; color: #fff; padding: 6px; border-radius: 4px;")
        btn_add.clicked.connect(self.add_provider)
        btn_del = QPushButton("- 删除")
        btn_del.setStyleSheet("background: rgba(255,82,82,0.2); color: #FF5252; padding: 6px; border-radius: 4px;")
        btn_del.clicked.connect(self.delete_provider)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        left_layout.addLayout(btn_layout)
        
        provider_layout.addLayout(left_layout, stretch=1)
        
        right_layout = QFormLayout()
        self.input_provider_name = QLineEdit()
        self.input_provider_base = QLineEdit()
        self.input_provider_key = QLineEdit()
        self.input_provider_key.setEchoMode(QLineEdit.Password)
        self.input_provider_model = QLineEdit()
        
        right_layout.addRow("配置名称:", self.input_provider_name)
        right_layout.addRow("API 地址:", self.input_provider_base)
        right_layout.addRow("API Key:", self.input_provider_key)
        right_layout.addRow("模型名称:", self.input_provider_model)
        
        btn_save_provider = QPushButton("保存当前配置")
        btn_save_provider.setStyleSheet("background: #00E676; color: #000; padding: 8px; border-radius: 6px; font-weight: bold;")
        btn_save_provider.clicked.connect(self.save_provider)
        right_layout.addRow(btn_save_provider)
        
        provider_layout.addLayout(right_layout, stretch=2)
        tabs.addTab(provider_tab, "API 配置管理")

        style_tab = QWidget()
        style_layout = QVBoxLayout(style_tab)
        style_layout.setContentsMargins(15, 15, 15, 15)
        style_label1 = QLabel("① 我的历史发言样本（粘贴你以前发的消息）：")
        style_label1.setStyleSheet("color: #00E676; font-weight: bold;")
        style_layout.addWidget(style_label1)
        self.sample_input = QTextEdit()
        self.sample_input.setPlaceholderText("例如：\n今天好累啊~\n不想干活\n绝了，这老师又拖堂\n我直接原地起飞🚀")
        self.sample_input.setFixedHeight(100)
        self.sample_input.setStyleSheet("QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #FFF; padding: 8px; }")
        style_layout.addWidget(self.sample_input)
        
        self.btn_extract_style = QPushButton("✨ 一键提取我的风格")
        self.btn_extract_style.setCursor(Qt.PointingHandCursor)
        self.btn_extract_style.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E676, stop:1 #00BFFF); color: #000; padding: 10px; border-radius: 6px; font-weight: bold; } QPushButton:hover { opacity: 0.8; }")
        self.btn_extract_style.clicked.connect(self.do_extract_style)
        style_layout.addWidget(self.btn_extract_style)

        style_label2 = QLabel("② 提取出的风格（可手动修改）：")
        style_label2.setStyleSheet("color: #00E676; font-weight: bold; margin-top: 10px;")
        style_layout.addWidget(style_label2)
        self.style_input = QTextEdit()
        self.style_input.setPlainText(self.config.get("personal_style", ""))
        self.style_input.setPlaceholderText("提取后的风格将在这里显示...")
        self.style_input.setStyleSheet("QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #FFF; padding: 8px; }")
        style_layout.addWidget(self.style_input)
        tabs.addTab(style_tab, "个人风格克隆")

        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        self.bg_label = QLabel(f"当前背景：{self.config.get('background_image') or '默认(无)'}")
        self.bg_label.setWordWrap(True)
        appearance_layout.addWidget(self.bg_label)
        btn_choose_bg = QPushButton("🖼️ 选择背景图片")
        btn_choose_bg.setStyleSheet("QPushButton { background: #3a3a3a; color: #fff; padding: 10px; border-radius: 6px; border: 1px solid #555; } QPushButton:hover { background: #4a4a4a; }")
        btn_choose_bg.clicked.connect(self.choose_bg)
        appearance_layout.addWidget(btn_choose_bg)
        btn_clear_bg = QPushButton("❌ 清除背景")
        btn_clear_bg.setStyleSheet("QPushButton { background: rgba(255,82,82,0.1); color: #FF5252; padding: 10px; border-radius: 6px; border: 1px solid rgba(255,82,82,0.3); } QPushButton:hover { background: rgba(255,82,82,0.2); }")
        btn_clear_bg.clicked.connect(self.clear_bg)
        appearance_layout.addWidget(btn_clear_bg)
        appearance_layout.addStretch()
        tabs.addTab(appearance_tab, "外观设置")

        advanced_tab = QWidget()
        advanced_layout = QFormLayout(advanced_tab)
        
        self.mad_cb = QCheckBox("允许生成【发疯型】回复")
        self.mad_cb.setChecked(self.config.get("enable_mad_style", True))
        self.mad_cb.setStyleSheet("QCheckBox { color: #CE93D8; font-weight: bold; }")
        advanced_layout.addRow(self.mad_cb)

        self.madder_cb = QCheckBox("允许生成【更疯型】回复")
        self.madder_cb.setChecked(self.config.get("enable_madder_style", True))
        self.madder_cb.setStyleSheet("QCheckBox { color: #CE93D8; font-weight: bold; }")
        advanced_layout.addRow(self.madder_cb)

        self.offend_cb = QCheckBox("允许生成【冒犯型】回复")
        self.offend_cb.setChecked(self.config.get("enable_offend_style", True))
        self.offend_cb.setStyleSheet("QCheckBox { color: #FF5252; font-weight: bold; }")
        advanced_layout.addRow(self.offend_cb)
        
        self.unlimited_cb = QCheckBox("开启无限上下文记忆（Token消耗极大）")
        self.unlimited_cb.setChecked(self.config.get("unlimited_memory", False))
        self.unlimited_cb.setStyleSheet("QCheckBox { color: #FFD700; font-weight: bold; }")
        advanced_layout.addRow(self.unlimited_cb)
        
        self.context_slider = QSlider(Qt.Horizontal)
        self.context_slider.setMinimum(0)
        self.context_slider.setMaximum(100)
        self.context_slider.setValue(self.config.get("context_length", 4))
        self.context_slider.setTickPosition(QSlider.TicksBelow)
        self.context_slider.setTickInterval(10)
        self.context_slider.valueChanged.connect(self.update_context_label)
        self.context_label = QLabel(f"当前记忆轮数：{self.config.get('context_length', 4)} 轮")
        self.context_label.setStyleSheet("color: #00E676; font-weight: bold;")
        self.context_warn = QLabel("⚠️ 提示：超过 10 轮会消耗巨量 Token；如果勾选了“无限记忆”，此滑块设置将被忽略。")
        self.context_warn.setStyleSheet("color: #FF5252; font-size: 11px;")
        self.context_warn.setWordWrap(True)
        advanced_layout.addRow("上下文记忆:", self.context_label)
        advanced_layout.addRow(self.context_slider)
        advanced_layout.addRow(self.context_warn)
        tabs.addTab(advanced_tab, "高级设置")
        
        session_tab = QWidget()
        session_layout = QVBoxLayout(session_tab)
        session_layout.setContentsMargins(15, 15, 15, 15)
        session_layout.addWidget(QLabel("在这里为每个会话设定对象的简介："))
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(2)
        self.session_table.setHorizontalHeaderLabels(["会话名称", "对象简介（性别、关系、性格等）"])
        self.session_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.session_table.setStyleSheet("QTableWidget { background: rgba(255,255,255,0.02); border: 1px solid #333; color: #fff; } QHeaderView::section { background: #333; color: #00E676; }")
        
        session_profiles = self.config.get("session_profiles", {})
        sessions = self.config.get("sessions", ["默认单聊"])
        self.session_table.setRowCount(len(sessions))
        for i, s in enumerate(sessions):
            self.session_table.setItem(i, 0, QTableWidgetItem(s))
            self.session_table.setItem(i, 1, QTableWidgetItem(session_profiles.get(s, "未知，普通朋友，语气适中")))
        session_layout.addWidget(self.session_table)
        tabs.addTab(session_tab, "会话与角色")
        
        layout.addWidget(tabs)
        
        btn_save = QPushButton("保存所有设置")
        btn_save.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E676, stop:1 #00BFFF); color: #000; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; } QPushButton:hover { opacity: 0.8; }")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)
        
        self.refresh_provider_list()

    def refresh_provider_list(self):
        self.provider_list.clear()
        providers = self.config.get("custom_providers", {})
        for name in providers:
            self.provider_list.addItem(name)
    
    def on_provider_selected(self, item):
        name = item.text()
        providers = self.config.get("custom_providers", {})
        if name in providers:
            cfg = providers[name]
            self.input_provider_name.setText(name)
            self.input_provider_base.setText(cfg.get("base_url", ""))
            self.input_provider_key.setText(cfg.get("api_key", ""))
            self.input_provider_model.setText(cfg.get("model", ""))

    def add_provider(self):
        self.input_provider_name.setText("新配置")
        self.input_provider_base.setText("")
        self.input_provider_key.setText("")
        self.input_provider_model.setText("")
        self.input_provider_name.setFocus()

    def delete_provider(self):
        name = self.input_provider_name.text().strip()
        if not name: return
        providers = self.config.get("custom_providers", {})
        if name in providers:
            if len(providers) <= 1:
                QMessageBox.warning(self, "提示", "至少需要保留一个 API 配置！")
                return
            reply = QMessageBox.question(self, "确认", f"确定要删除配置【{name}】吗？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del providers[name]
                self.config["custom_providers"] = providers
                if self.config["current_provider"] == name:
                    self.config["current_provider"] = list(providers.keys())[0]
                save_config(self.config)
                self.refresh_provider_list()
                self.input_provider_name.clear()
                self.input_provider_base.clear()
                self.input_provider_key.clear()
                self.input_provider_model.clear()

    def save_provider(self):
        name = self.input_provider_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入配置名称！")
            return
        providers = self.config.get("custom_providers", {})
        providers[name] = {
            "base_url": self.input_provider_base.text().strip(),
            "api_key": self.input_provider_key.text().strip(),
            "model": self.input_provider_model.text().strip()
        }
        self.config["custom_providers"] = providers
        self.config["current_provider"] = name
        save_config(self.config)
        self.refresh_provider_list()
        QMessageBox.information(self, "成功", f"配置【{name}】已保存！")

    def do_extract_style(self):
        sample = self.sample_input.toPlainText().strip()
        if not sample:
            QMessageBox.warning(self, "提示", "请先粘贴你的历史发言样本！")
            return
        self.btn_extract_style.setText("⏳ 正在提取风格...")
        self.btn_extract_style.setEnabled(False)
        QApplication.processEvents()
        extracted_style = extract_style_from_sample(sample)
        self.style_input.setPlainText(extracted_style)
        self.btn_extract_style.setText("✨ 一键提取我的风格")
        self.btn_extract_style.setEnabled(True)
        QMessageBox.information(self, "成功", "风格提取完成！请点击下方的“保存所有设置”按钮生效。")

    def update_context_label(self, value):
        self.context_label.setText(f"当前记忆轮数：{value} 轮")
        self.context_label.setStyleSheet(f"color: {'#FF5252' if value >= 20 else '#00E676'}; font-weight: bold;")

    def choose_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择背景图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.config["background_image"] = file_path
            self.bg_label.setText(f"当前背景：{file_path}")
    def clear_bg(self):
        self.config["background_image"] = ""
        self.bg_label.setText("当前背景：默认（无）")

    def save(self):
        self.config["context_length"] = self.context_slider.value()
        self.config["unlimited_memory"] = self.unlimited_cb.isChecked()
        self.config["enable_mad_style"] = self.mad_cb.isChecked()
        self.config["enable_madder_style"] = self.madder_cb.isChecked()
        self.config["enable_offend_style"] = self.offend_cb.isChecked()
        self.config["personal_style"] = self.style_input.toPlainText().strip()
        
        profiles = {}
        for row in range(self.session_table.rowCount()):
            s_name = self.session_table.item(row, 0).text()
            s_profile = self.session_table.item(row, 1).text()
            profiles[s_name] = s_profile
        self.config["session_profiles"] = profiles
        
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
        self.current_image_base64 = None
        self.initUI()
        self.initTray()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(460, 600)
        self.resize(580, 880)
        self.setWindowTitle("Cf 聊天助手 v2.3")
        
        main_outer_layout = QHBoxLayout(self)
        main_outer_layout.setContentsMargins(15, 15, 15, 15)
        main_outer_layout.setSpacing(10)
        
        self.container = BackgroundFrame()
        self.container.setStyleSheet("BackgroundFrame { background: transparent; }")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.container.setGraphicsEffect(shadow)
        
        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(25, 20, 25, 20)
        self.inner_layout.setSpacing(12)

        top_bar = QHBoxLayout()
        self.title_bar = QLabel("💬  Cf v2.3")
        self.title_bar.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; background: transparent;")
        
        self.session_combo = QComboBox()
        config = load_config()
        for s in config.get("sessions", ["默认单聊"]):
            self.session_combo.addItem(s)
        self.session_combo.setCurrentText(config.get("current_session", "默认单聊"))
        self.session_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,0.05); color: #FFD700; border: 1px solid rgba(255,215,0,0.3); border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: bold; } QComboBox:hover { background: rgba(255,255,255,0.1); } QComboBox::drop-down { border: none; width: 20px; } QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #FFD700; margin-right: 5px; }")
        self.session_combo.currentIndexChanged.connect(self.change_session)
        
        self.btn_add_session = QPushButton("+")
        self.btn_add_session.setFixedSize(24, 24)
        self.btn_add_session.setCursor(Qt.PointingHandCursor)
        self.btn_add_session.setStyleSheet("QPushButton { background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.3); color: #FFD700; font-size: 14px; border-radius: 12px; } QPushButton:hover { background: rgba(255,215,0,0.3); }")
        self.btn_add_session.clicked.connect(self.add_session)

        self.btn_profile = QPushButton("👤")
        self.btn_profile.setFixedSize(24, 24)
        self.btn_profile.setCursor(Qt.PointingHandCursor)
        self.btn_profile.setStyleSheet("QPushButton { background: rgba(0,191,255,0.1); border: 1px solid rgba(0,191,255,0.3); color: #00BFFF; font-size: 12px; border-radius: 12px; } QPushButton:hover { background: rgba(0,191,255,0.3); }")
        self.btn_profile.clicked.connect(self.edit_profile)

        self.chat_mode_combo = QComboBox()
        self.chat_mode_combo.addItem("单聊", "single")
        self.chat_mode_combo.addItem("水群", "group")
        self.chat_mode_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,0.05); color: #00BFFF; border: 1px solid rgba(0,150,255,0.3); border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: bold; } QComboBox:hover { background: rgba(255,255,255,0.1); } QComboBox::drop-down { border: none; } QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #00BFFF; margin-right: 5px; }")
        self.chat_mode_combo.setCurrentIndex(0 if config.get("chat_mode") == "single" else 1)
        self.chat_mode_combo.currentIndexChanged.connect(self.change_chat_mode)
        
        self.provider_combo = QComboBox()
        self.provider_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,0.05); color: #00E676; border: 1px solid rgba(0,200,120,0.3); border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: bold; } QComboBox:hover { background: rgba(255,255,255,0.1); } QComboBox::drop-down { border: none; } QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #00E676; margin-right: 5px; }")
        self.provider_combo.currentIndexChanged.connect(self.change_provider)
        
        self.btn_history = QPushButton("📜")
        self.btn_history.setFixedSize(28, 28)
        self.btn_history.setCursor(Qt.PointingHandCursor)
        self.btn_history.setStyleSheet("QPushButton { background: transparent; border: none; color: #888; font-size: 16px; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 14px; }")
        self.btn_history.clicked.connect(self.toggle_history)
        
        self.btn_help = QPushButton("❓")
        self.btn_help.setFixedSize(28, 28)
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setStyleSheet("QPushButton { background: transparent; border: none; color: #888; font-size: 16px; font-weight: bold; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 14px; }")
        self.btn_help.clicked.connect(self.open_help)
        
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setFixedSize(28, 28)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setStyleSheet("QPushButton { background: transparent; border: none; color: #888; font-size: 16px; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 14px; }")
        self.btn_settings.clicked.connect(self.open_settings)

        self.btn_minimize = QPushButton("➖")
        self.btn_minimize.setFixedSize(28, 28)
        self.btn_minimize.setCursor(Qt.PointingHandCursor)
        self.btn_minimize.setStyleSheet("QPushButton { background: transparent; border: none; color: #888; font-size: 14px; font-weight: bold; } QPushButton:hover { color: #FFF; background-color: rgba(255,255,255,0.1); border-radius: 14px; }")
        self.btn_minimize.clicked.connect(self.showMinimized)

        self.btn_close = QPushButton("✖")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("QPushButton { background: transparent; border: none; color: #888; font-size: 14px; font-weight: bold; } QPushButton:hover { color: #FFF; background-color: rgba(255,82,82,0.5); border-radius: 14px; }")
        self.btn_close.clicked.connect(self.close)
        
        top_bar.addWidget(self.title_bar)
        top_bar.addStretch()
        top_bar.addWidget(self.session_combo)
        top_bar.addWidget(self.btn_add_session)
        top_bar.addWidget(self.btn_profile)
        top_bar.addWidget(self.chat_mode_combo)
        top_bar.addWidget(self.provider_combo)
        top_bar.addWidget(self.btn_history)
        top_bar.addWidget(self.btn_help)
        top_bar.addWidget(self.btn_settings)
        top_bar.addWidget(self.btn_minimize)
        top_bar.addWidget(self.btn_close)
        self.inner_layout.addLayout(top_bar)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255,255,255,0.06); max-height: 1px;")
        self.inner_layout.addWidget(line)

        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setVisible(False)
        self.image_preview.setStyleSheet("QLabel { background: rgba(0,0,0,0.4); border-radius: 12px; border: 1px dashed rgba(0,200,120,0.6); }")
        self.image_preview.setFixedHeight(120)
        self.inner_layout.addWidget(self.image_preview)
        
        self.btn_clear_image = QPushButton("❌ 移除图片")
        self.btn_clear_image.setVisible(False)
        self.btn_clear_image.setCursor(Qt.PointingHandCursor)
        self.btn_clear_image.setStyleSheet("QPushButton { background: rgba(255,82,82,0.15); color: #FF5252; border: 1px solid rgba(255,82,82,0.4); border-radius: 6px; padding: 6px; font-size: 11px; } QPushButton:hover { background: rgba(255,82,82,0.3); }")
        self.btn_clear_image.clicked.connect(self.clear_image)
        self.inner_layout.addWidget(self.btn_clear_image)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("📋 在此粘贴或输入聊天记录...\n(输入框为空时，按快捷键会直接读取剪贴板)")
        self.input_box.setFixedHeight(80)
        self.input_box.setStyleSheet("QTextEdit { background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; color: #FFF; padding: 12px; font-size: 13px; font-family: 'Microsoft YaHei'; } QTextEdit:focus { border: 1px solid #00E676; background: rgba(0,0,0,0.3); }")
        self.inner_layout.addWidget(self.input_box)

        self.btn_analyze = QPushButton("🚀 开始分析")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0, 230, 118, 0.8), stop:1 rgba(0, 191, 255, 0.8)); color: #000; border: none; border-radius: 10px; padding: 12px; font-size: 15px; font-weight: bold; } QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0, 230, 118, 1), stop:1 rgba(0, 191, 255, 1)); } QPushButton:pressed { background: rgba(0, 200, 120, 0.5); }")
        self.btn_analyze.clicked.connect(self.analyze_requested.emit)
        self.inner_layout.addWidget(self.btn_analyze)

        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: rgba(255,255,255,0.06); max-height: 1px;")
        self.inner_layout.addWidget(line2)

        self.label_content = QLabel()
        self.label_content.setWordWrap(True)
        self.label_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_content.setStyleSheet("color: #E0E0E0; background: transparent;")
        self.label_content.setText("<div style='font-family: \"Microsoft YaHei\", sans-serif; color: #AAA; font-size: 13px; text-align: center; margin-top: 30px;'><p style='font-size: 40px; margin-bottom: 15px;'>👋</p><p style='font-size: 16px; color: #FFF; font-weight: bold;'>Cf 助手 v2.3 已就绪</p><p style='font-size: 12px; margin-top: 5px;'>支持人物设定、风格克隆、截图分析</p></div>")
        self.inner_layout.addWidget(self.label_content)

        self.persona_label = QLabel()
        self.persona_label.setWordWrap(True)
        self.persona_label.setVisible(False)
        self.persona_label.setStyleSheet("color: #FFD700; font-size: 12px; background: rgba(255, 215, 0, 0.05); border: 1px solid rgba(255, 215, 0, 0.2); border-radius: 8px; padding: 10px; margin-top: 5px;")
        self.inner_layout.addWidget(self.persona_label)

        self.advice_label = QLabel()
        self.advice_label.setWordWrap(True)
        self.advice_label.setVisible(False)
        self.advice_label.setStyleSheet("color: #00BFFF; font-size: 13px; background: rgba(0, 191, 255, 0.08); border: 1px solid rgba(0, 191, 255, 0.3); border-radius: 8px; padding: 10px; margin-top: 5px; font-weight: bold;")
        self.inner_layout.addWidget(self.advice_label)

        self.reply_buttons = []
        for i in range(6):
            btn = QPushButton()
            btn.setVisible(False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background-color: rgba(0, 200, 120, 0.15); color: #00E676; border: 1px solid rgba(0, 200, 120, 0.3); border-radius: 12px; padding: 12px 16px; font-size: 13px; text-align: left; } QPushButton:hover { background-color: rgba(0, 200, 120, 0.3); border-color: #00E676; } QPushButton:pressed { background-color: rgba(0, 200, 120, 0.5); }")
            btn.clicked.connect(lambda checked, b=btn: self._copy_reply(b))
            self.inner_layout.addWidget(btn)
            self.reply_buttons.append(btn)

        self.inner_layout.addStretch()

        bottom_bar = QHBoxLayout()
        self.hint_label = QLabel("按 Esc 关闭 | 按住窗口拖动 | 右下角拉伸")
        self.hint_label.setStyleSheet("color: #555; font-size: 10px; background: transparent;")
        bottom_bar.addWidget(self.hint_label)
        bottom_bar.addStretch()

        self.btn_clear_context = QPushButton("🧠 清空当前记忆")
        self.btn_clear_context.setCursor(Qt.PointingHandCursor)
        self.btn_clear_context.setStyleSheet("QPushButton { background: transparent; border: none; color: #777; font-size: 11px; } QPushButton:hover { color: #FF5252; text-decoration: underline; }")
        bottom_bar.addWidget(self.btn_clear_context)

        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: rgba(0, 200, 120, 0.3); border-radius: 3px; width: 12px; height: 12px; } QSizeGrip:hover { background-color: rgba(0, 200, 120, 0.7); }")
        bottom_bar.addWidget(self.sizegrip, 0, Qt.AlignBottom | Qt.AlignRight)
        
        self.inner_layout.addLayout(bottom_bar)
        main_outer_layout.addWidget(self.container, stretch=1)

        self.history_panel = QFrame()
        self.history_panel.setVisible(False)
        self.history_panel.setFixedWidth(220)
        self.history_panel.setStyleSheet("QFrame { background: rgba(20, 20, 25, 0.95); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05); }")
        history_layout = QVBoxLayout(self.history_panel)
        history_layout.setContentsMargins(15, 15, 15, 15)
        self.title_his = QLabel("📜 历史记录")
        self.title_his.setStyleSheet("color: #FFF; font-size: 14px; font-weight: bold; padding-bottom: 5px; border-bottom: 1px solid #333;")
        history_layout.addWidget(self.title_his)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #CCC; font-size: 12px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.03); border-radius: 6px; }
            QListWidget::item:hover { background: rgba(255,255,255,0.05); }
            QListWidget::item:selected { background: rgba(0, 200, 120, 0.2); color: #00E676; }
            QScrollBar:vertical { border: none; background: transparent; width: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.1); border-radius: 2px; }
        """)
        self.history_list.itemClicked.connect(self.load_history_item)
        history_layout.addWidget(self.history_list)
        btn_clear_hist = QPushButton("🗑️ 清空历史")
        btn_clear_hist.setStyleSheet("QPushButton { background: rgba(255,82,82,0.08); color: #FF5252; border: 1px solid rgba(255,82,82,0.2); border-radius: 8px; padding: 8px; font-size: 12px; } QPushButton:hover { background: rgba(255,82,82,0.2); }")
        btn_clear_hist.clicked.connect(self.clear_all_history)
        history_layout.addWidget(btn_clear_hist)
        main_outer_layout.addWidget(self.history_panel)
        self.apply_background(config.get("background_image", ""))
        
        self.refresh_provider_combo()

    def initTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 230, 118))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 32, 32)
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "Cf")
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Cf 聊天助手 v2.3")
        
        tray_menu = QMenu()
        show_action = QAction("显示主界面", self)
        show_action.triggered.connect(self.show_window)
        quit_action = QAction("彻底退出", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_window()

    def show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Cf 助手",
            "已最小化到系统托盘，双击图标重新打开。",
            QSystemTrayIcon.Information,
            2000
        )

    def refresh_provider_combo(self):
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        config = load_config()
        providers = config.get("custom_providers", {})
        current = config.get("current_provider", "")
        for name in providers:
            self.provider_combo.addItem(name)
        if current in providers:
            self.provider_combo.setCurrentText(current)
        self.provider_combo.blockSignals(False)

    def change_provider(self, index):
        config = load_config()
        config["current_provider"] = self.provider_combo.currentText()
        save_config(config)
        self.show_status(f"✅ 已切换 API 配置：{config['current_provider']}")

    def edit_profile(self):
        session_name = self.session_combo.currentText()
        dialog = ProfileDialog(session_name, self)
        if dialog.exec_() == QDialog.Accepted:
            profile_text = dialog.profile_input.toPlainText().strip()
            config = load_config()
            config.setdefault("session_profiles", {})[session_name] = profile_text
            save_config(config)
            self.show_status(f"✅ 已更新【{session_name}】的对象简介")

    def set_image_preview(self, base64_str):
        self.current_image_base64 = base64_str
        image_data = base64.b64decode(base64_str)
        image = QImage()
        image.loadFromData(image_data)
        pixmap = QPixmap.fromImage(image)
        scaled_pix = pixmap.scaled(400, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_preview.setPixmap(scaled_pix)
        self.image_preview.setVisible(True)
        self.btn_clear_image.setVisible(True)
        self.show_status("🖼️ 已读取剪贴板图片")

    def clear_image(self):
        self.current_image_base64 = None
        self.image_preview.clear()
        self.image_preview.setVisible(False)
        self.btn_clear_image.setVisible(False)

    def change_session(self, index):
        session_name = self.session_combo.currentText()
        config = load_config()
        config["current_session"] = session_name
        save_config(config)
        self.title_his.setText(f"📜 {session_name}")
        if self.is_history_open: self.refresh_history_list()
        self.show_status(f"✅ 已切换至会话：{session_name}")

    def add_session(self):
        text, ok = QInputDialog.getText(self, "新建会话", "请输入会话名称（例如：张三、摸鱼群）：")
        if ok and text.strip():
            session_name = text.strip()
            config = load_config()
            if session_name not in config.get("sessions", []):
                config.setdefault("sessions", []).append(session_name)
                config["current_session"] = session_name
                save_config(config)
                self.session_combo.addItem(session_name)
                self.session_combo.setCurrentText(session_name)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                pass
            else:
                self.activateWindow()
                self.raise_()
        super().changeEvent(event)

    def toggle_history(self):
        self.is_history_open = not self.is_history_open
        if self.is_history_open:
            self.history_panel.setVisible(True)
            self.setMinimumWidth(800)
            self.resize(800, self.height())
            self.refresh_history_list()
        else:
            self.history_panel.setVisible(False)
            self.setMinimumWidth(460)
            self.resize(580, self.height())

    def refresh_history_list(self):
        self.history_list.clear()
        session_name = self.session_combo.currentText()
        records = load_history(session_name)
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
        reply = QMessageBox.question(self, "确认", "确定要清空当前会话的历史记录吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            clear_history(self.session_combo.currentText())
            self.refresh_history_list()
            self.show_status("🗑️ 历史记录已清空")

    def open_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cf 助手 - 帮助与排错")
        dialog.setFixedSize(520, 580)
        dialog.setStyleSheet("background-color: #1e1e24; color: #fff; font-size: 13px; border-radius: 12px;")
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("background: transparent; border: none; color: #E0E0E0; font-size: 13px; line-height: 1.6;")
        html_content = """
        <h3 style='color: #00E676;'>🚀 Cf 助手 v2.3 使用说明</h3>
        <p><b>🔑 核心快捷键：</b></p>
        <ul>
            <li><b>Ctrl+Shift+J</b>：优先分析输入框内容（含图片）；否则分析剪贴板内容</li>
            <li><b>Ctrl+Shift+S</b>：打开设置面板</li>
            <li><b>Ctrl+Shift+Q</b>：彻底退出 Cf 助手</li>
        </ul>
        <p><b>⚙️ 窗口行为：</b></p>
        <ul>
            <li>点击右上角 <b>➖</b> 可将窗口最小化到任务栏。</li>
            <li>点击右上角 <b>✖</b> 可将窗口最小化到系统托盘（右下角）。</li>
            <li>双击系统托盘图标，或右键选择“显示主界面”，即可重新唤出窗口。</li>
            <li>窗口不再强制置顶，可被其他窗口覆盖。点击窗口任意位置或任务栏图标可重新激活。</li>
        </ul>
        <p><b>⚙️ API 配置管理：</b></p>
        <ul>
            <li>在设置 -> API 配置管理中，你可以自由添加、修改、删除多套 API 配置。</li>
            <li>支持任何兼容 OpenAI 格式的 API（如 DeepSeek、Kimi、LM Studio、vLLM 等）。</li>
        </ul>
        <p><b>⚡ v2.3 性能优化：</b></p>
        <ul>
            <li>加入了请求防抖锁，防止连续按键被限流。</li>
            <li>自动压缩截图（限制尺寸+转JPEG），极大提升校园网传输速度。</li>
        </ul>
        """
        browser.setHtml(html_content)
        layout.addWidget(browser)
        btn_close = QPushButton("我知道了")
        btn_close.setStyleSheet("background-color: #00E676; color: #000; padding: 10px; border-radius: 8px; font-weight: bold;")
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
            current_chat_mode = config.get("chat_mode", "single")
            self.chat_mode_combo.blockSignals(True)
            self.chat_mode_combo.setCurrentIndex(0 if current_chat_mode == "single" else 1)
            self.chat_mode_combo.blockSignals(False)
            self.apply_background(config.get("background_image", ""))
            self.refresh_provider_combo()
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
        action_advice = data.get("action_advice", "")
        persona_analysis = data.get("persona_analysis", {})

        if persona_analysis:
            persona_html = "<b>🕵️ 群友透视：</b><br>"
            for name, trait in persona_analysis.items():
                persona_html += f"• <b>{name}</b>：{trait}<br>"
            self.persona_label.setText(persona_html)
            self.persona_label.setVisible(True)
        else:
            self.persona_label.setVisible(False)

        if action_advice and action_advice.strip() and action_advice.strip() != "无":
            self.advice_label.setText(f"💡 行动建议：{action_advice}")
            self.advice_label.setVisible(True)
        else:
            self.advice_label.setVisible(False)

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
                prediction = r.get('prediction', '')
                
                if prediction:
                    display_text = f"[{style}] {text}\n⤷ 预测对方：{prediction}"
                else:
                    display_text = f"[{style}] {text}"
                
                if style == "冒犯型":
                    btn.setStyleSheet("QPushButton { background-color: rgba(255, 50, 50, 0.15); color: #FF5252; border: 1px solid rgba(255, 50, 50, 0.6); border-radius: 12px; padding: 12px 16px; font-size: 13px; text-align: left; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 50, 50, 0.3); border-color: #FF5252; } QPushButton:pressed { background-color: rgba(255, 50, 50, 0.5); }")
                    btn.setText(f"💀 [终极冒犯·易被封号] {display_text}")
                elif style in ["发疯型", "更疯型"]:
                    btn.setStyleSheet("QPushButton { background-color: rgba(156, 39, 176, 0.15); color: #CE93D8; border: 1px solid rgba(156, 39, 176, 0.4); border-radius: 12px; padding: 12px 16px; font-size: 13px; text-align: left; } QPushButton:hover { background-color: rgba(156, 39, 176, 0.3); border-color: #CE93D8; } QPushButton:pressed { background-color: rgba(156, 39, 176, 0.5); }")
                    btn.setText(display_text)
                else:
                    btn.setStyleSheet("QPushButton { background-color: rgba(0, 200, 120, 0.15); color: #00E676; border: 1px solid rgba(0, 200, 120, 0.3); border-radius: 12px; padding: 12px 16px; font-size: 13px; text-align: left; } QPushButton:hover { background-color: rgba(0, 200, 120, 0.3); border-color: #00E676; } QPushButton:pressed { background-color: rgba(0, 200, 120, 0.5); }")
                    btn.setText(display_text)
                
                btn.setProperty("reply_text", text)
                btn.setVisible(True)
            else:
                btn.setVisible(False)

        self.show()
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.activateWindow()
            self.raise_()
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