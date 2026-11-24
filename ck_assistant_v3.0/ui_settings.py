import os
import sys
import base64
from PyQt5.QtWidgets import (QApplication, QDialog, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
                             QMessageBox, QTextEdit, QFileDialog, QTabWidget,
                             QLabel, QCheckBox, QSlider, QTableWidget,
                             QTableWidgetItem, QHeaderView, QScrollArea, QWidget,
                             QFrame, QListWidget)
from PyQt5.QtCore import Qt
from engine import (load_config, save_config, DEFAULT_CONFIG)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cf 助手 v3.1 设置")
        self.setFixedSize(750, 850) # 窗口稍微加宽，方便查看
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: #e0e0e0; font-size: 13px; }
            QLabel { color: #aaa; }
            QLineEdit, QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; padding: 8px; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #00E676; }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { border: none; background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.config = load_config()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #26262e; border-radius: 8px; }
            QTabBar::tab { background: #1e1e24; color: #888; padding: 10px 18px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #26262e; color: #00E676; border-bottom: 2px solid #00E676; }
            QTabBar::tab:hover { background: #2a2a33; }
        """)
        
        provider_tab = QWidget()
        provider_layout = QHBoxLayout(provider_tab)
        provider_layout.setContentsMargins(20, 20, 20, 20)
        provider_layout.setSpacing(15)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.addWidget(QLabel("已保存的 API 配置："))
        self.provider_list = QListWidget()
        self.provider_list.setStyleSheet("QListWidget { background: rgba(255,255,255,0.02); border: 1px solid #333; color: #fff; border-radius: 6px; } QListWidget::item { padding: 10px; } QListWidget::item:selected { background: #00E676; color: #000; border-radius: 4px; }")
        self.provider_list.itemClicked.connect(self.on_provider_selected)
        left_layout.addWidget(self.provider_list)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_add = QPushButton("+ 新增")
        btn_add.setStyleSheet("background: #3a3a3a; color: #fff; padding: 8px; border-radius: 6px; font-weight: bold;")
        btn_add.clicked.connect(self.add_provider)
        btn_del = QPushButton("- 删除")
        btn_del.setStyleSheet("background: rgba(255,82,82,0.2); color: #FF5252; padding: 8px; border-radius: 6px; font-weight: bold;")
        btn_del.clicked.connect(self.delete_provider)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        left_layout.addLayout(btn_layout)
        provider_layout.addLayout(left_layout, stretch=1)
        
        right_layout = QFormLayout()
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(10, 10, 10, 10)
        self.input_provider_name = QLineEdit()
        self.input_provider_base = QLineEdit()
        
        # 【新增】API Key 输入框，带有显示/隐藏按钮
        key_layout = QHBoxLayout()
        self.input_provider_key = QLineEdit()
        self.input_provider_key.setEchoMode(QLineEdit.Password)
        self.btn_toggle_key = QPushButton("👁️")
        self.btn_toggle_key.setFixedSize(30, 30)
        self.btn_toggle_key.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_key.setStyleSheet("QPushButton { background: transparent; border: none; color: #aaa; font-size: 14px; } QPushButton:hover { color: #fff; }")
        self.btn_toggle_key.clicked.connect(self.toggle_key_visibility)
        key_layout.addWidget(self.input_provider_key)
        key_layout.addWidget(self.btn_toggle_key)
        
        self.input_provider_model = QLineEdit()
        right_layout.addRow("配置名称:", self.input_provider_name)
        right_layout.addRow("API 地址:", self.input_provider_base)
        right_layout.addRow("API Key:", key_layout)
        right_layout.addRow("模型名称:", self.input_provider_model)
        
        btn_save_provider = QPushButton("保存当前配置")
        btn_save_provider.setStyleSheet("background: #00E676; color: #000; padding: 10px; border-radius: 8px; font-weight: bold; margin-top: 10px;")
        btn_save_provider.clicked.connect(self.save_provider)
        right_layout.addRow(btn_save_provider)
        provider_layout.addLayout(right_layout, stretch=2)
        tabs.addTab(provider_tab, "API 配置管理")

        style_tab = QWidget()
        style_layout = QVBoxLayout(style_tab)
        style_layout.setContentsMargins(20, 20, 20, 20)
        style_layout.setSpacing(12)
        style_label1 = QLabel("① 我的历史发言样本（粘贴你以前发的消息）：")
        style_label1.setStyleSheet("color: #00E676; font-weight: bold;")
        style_layout.addWidget(style_label1)
        self.sample_input = QTextEdit()
        self.sample_input.setPlaceholderText("例如：\n今天好累啊~\n不想干活\n绝了，这老师又拖堂\n我直接原地起飞🚀")
        self.sample_input.setFixedHeight(120)
        self.sample_input.setStyleSheet("QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #FFF; padding: 10px; }")
        style_layout.addWidget(self.sample_input)
        self.btn_extract_style = QPushButton("✨ 一键提取我的风格")
        self.btn_extract_style.setCursor(Qt.PointingHandCursor)
        self.btn_extract_style.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E676, stop:1 #00BFFF); color: #000; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; } QPushButton:hover { opacity: 0.8; }")
        self.btn_extract_style.clicked.connect(self.do_extract_style)
        style_layout.addWidget(self.btn_extract_style)
        style_label2 = QLabel("② 提取出的风格（可手动修改）：")
        style_label2.setStyleSheet("color: #00E676; font-weight: bold; margin-top: 10px;")
        style_layout.addWidget(style_label2)
        self.style_input = QTextEdit()
        self.style_input.setPlainText(self.config.get("personal_style", ""))
        self.style_input.setPlaceholderText("提取后的风格将在这里显示...")
        self.style_input.setStyleSheet("QTextEdit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #FFF; padding: 10px; }")
        style_layout.addWidget(self.style_input)
        tabs.addTab(style_tab, "个人风格克隆")

        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        appearance_layout.setContentsMargins(20, 20, 20, 20)
        appearance_layout.setSpacing(15)
        self.bg_label = QLabel(f"当前背景：{self.config.get('background_image') or '默认(无)'}")
        self.bg_label.setWordWrap(True)
        appearance_layout.addWidget(self.bg_label)
        btn_choose_bg = QPushButton("🖼️ 选择背景图片")
        btn_choose_bg.setStyleSheet("QPushButton { background: #3a3a3a; color: #fff; padding: 12px; border-radius: 8px; border: 1px solid #555; } QPushButton:hover { background: #4a4a4a; }")
        btn_choose_bg.clicked.connect(self.choose_bg)
        appearance_layout.addWidget(btn_choose_bg)
        btn_clear_bg = QPushButton("❌ 清除背景")
        btn_clear_bg.setStyleSheet("QPushButton { background: rgba(255,82,82,0.1); color: #FF5252; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,82,82,0.3); } QPushButton:hover { background: rgba(255,82,82,0.2); }")
        btn_clear_bg.clicked.connect(self.clear_bg)
        appearance_layout.addWidget(btn_clear_bg)
        appearance_layout.addStretch()
        tabs.addTab(appearance_tab, "外观设置")

        advanced_tab = QWidget()
        advanced_main_layout = QVBoxLayout(advanced_tab)
        advanced_main_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        advanced_layout = QFormLayout(scroll_content)
        advanced_layout.setContentsMargins(20, 20, 20, 20)
        advanced_layout.setSpacing(15)
        
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
        self.input_height_slider = QSlider(Qt.Horizontal)
        self.input_height_slider.setMinimum(80)
        self.input_height_slider.setMaximum(400)
        self.input_height_slider.setSingleStep(10)
        self.input_height_slider.setValue(self.config.get("input_height", 120))
        self.input_height_slider.valueChanged.connect(self.update_input_height_label)
        self.input_height_label = QLabel(f"当前输入框高度：{self.config.get('input_height', 120)} px")
        self.input_height_label.setStyleSheet("color: #00E676; font-weight: bold;")
        advanced_layout.addRow("输入框大小:", self.input_height_label)
        advanced_layout.addRow(self.input_height_slider)
        scroll.setWidget(scroll_content)
        advanced_main_layout.addWidget(scroll)
        tabs.addTab(advanced_tab, "高级设置")
        
        session_tab = QWidget()
        session_layout = QVBoxLayout(session_tab)
        session_layout.setContentsMargins(20, 20, 20, 20)
        session_layout.setSpacing(10)
        session_layout.addWidget(QLabel("在这里为每个会话设定对象的简介："))
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(2)
        self.session_table.setHorizontalHeaderLabels(["会话名称", "对象简介（性别、关系、性格等）"])
        self.session_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.session_table.setStyleSheet("QTableWidget { background: rgba(255,255,255,0.02); border: 1px solid #333; color: #fff; border-radius: 6px; } QHeaderView::section { background: #333; color: #00E676; padding: 6px; }")
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
        btn_save.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E676, stop:1 #00BFFF); color: #000; padding: 14px; border-radius: 10px; font-weight: bold; font-size: 15px; } QPushButton:hover { opacity: 0.8; }")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)
        self.refresh_provider_list()

    # 【核心修复】切换密码可见性
    def toggle_key_visibility(self):
        if self.input_provider_key.echoMode() == QLineEdit.Password:
            self.input_provider_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key.setStyleSheet("QPushButton { background: transparent; border: none; color: #00E676; font-size: 14px; } QPushButton:hover { color: #fff; }")
        else:
            self.input_provider_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setStyleSheet("QPushButton { background: transparent; border: none; color: #aaa; font-size: 14px; } QPushButton:hover { color: #fff; }")

    def update_input_height_label(self, value):
        self.input_height_label.setText(f"当前输入框高度：{value} px")
    def refresh_provider_list(self):
        self.provider_list.clear()
        providers = self.config.get("custom_providers", {})
        for name in providers: self.provider_list.addItem(name)
    def on_provider_selected(self, item):
        name = item.text()
        providers = self.config.get("custom_providers", {})
        if name in providers:
            cfg = providers[name]
            self.input_provider_name.setText(name)
            self.input_provider_base.setText(cfg.get("base_url", ""))
            self.input_provider_key.setText(cfg.get("api_key", ""))
            self.input_provider_model.setText(cfg.get("model", ""))
            # 切换配置时，默认重置为隐藏密码
            self.input_provider_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setStyleSheet("QPushButton { background: transparent; border: none; color: #aaa; font-size: 14px; } QPushButton:hover { color: #fff; }")
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
        self.config["input_height"] = self.input_height_slider.value()
        profiles = {}
        for row in range(self.session_table.rowCount()):
            s_name = self.session_table.item(row, 0).text()
            s_profile = self.session_table.item(row, 1).text()
            profiles[s_name] = s_profile
        self.config["session_profiles"] = profiles
        save_config(self.config)
        QMessageBox.information(self, "成功", "配置已保存！")
        self.accept()

