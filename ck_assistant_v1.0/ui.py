import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal

class CfWindow(QWidget):
    # 定义信号，用于跨线程传递数据
    update_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        # 连接信号和槽函数
        self.update_signal.connect(self.update_data)
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(420, 480)
        
        layout = QVBoxLayout()
        self.label_content = QLabel()
        self.label_content.setWordWrap(True)
        self.label_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        layout.addWidget(self.label_content)
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(45, 45, 45, 240); 
                border-radius: 12px; 
                padding: 15px;
            }
        """)

    def update_data(self, data):
        surface = data.get("surface_answer", "分析中...")
        surface_probs = data.get("surface_probs", {})
        deep_intents = data.get("deep_intents", {})
        affinity = data.get("affinity_score", 50)
        danger = data.get("danger_level", 0)
        action = data.get("best_action", "无")
        reply = data.get("suggested_reply", "无")

        surface_html = "".join([f"<li>{k}：{v}%</li>" for k, v in surface_probs.items()]) if surface_probs else "<li>计算中...</li>"
        deep_html = "".join([f"<li>{k}：{v}%</li>" for k, v in deep_intents.items()]) if deep_intents else "<li>分析中...</li>"

        # 防崩溃判断
        if isinstance(affinity, (int, float)):
            affinity_color = "#00FF00" if affinity >= 80 else ("#FFD700" if affinity >= 40 else "#FF4500")
            affinity_display = f"{affinity} / 100"
        else:
            affinity_color = "#FF69B4"
            affinity_display = f"{affinity}"

        html_content = f"""
        <div style='color: #E0E0E0; font-family: "Microsoft YaHei", sans-serif; font-size: 13px;'>
            <p style='margin: 0 0 5px 0; font-weight: bold; font-size: 15px; color: #FFFFFF;'>Cf 读心分析：</p >
            <p style='margin: 0 0 5px 0; font-weight: bold; color: #E0E0E0;'>表层含义：{surface}</p >
            <ul style='margin: 0 0 10px 0; padding-left: 20px; color: #A0A0A0;'>{surface_html}</ul>
            
            <p style='margin: 0 0 5px 0; font-weight: bold; color: #FFFFFF;'>当前真实意图</p >
            <ul style='margin: 0 0 10px 0; padding-left: 20px; color: #A0A0A0;'>{deep_html}</ul>
            
            <p style='margin: 0 0 5px 0; color: {affinity_color}; font-weight: bold;'>好感度：{affinity_display}</p >
            <p style='margin: 0 0 5px 0; color: #FFD700; font-weight: bold;'>危险等级：{danger} / 10</p >
            <p style='margin: 0 0 5px 0; color: #00BFFF;'>最佳动作：{action}</p >
            
            <hr style='border: 0; border-top: 1px solid #555; margin: 10px 0;'>
            <p style='margin: 0; color: #00FF00; font-weight: bold; line-height: 1.6;'>💬 建议回复：<br>{reply}</p >
        </div>
        """
        self.label_content.setText(html_content)
        self.show()
        
    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = event.globalPos() - self.oldPos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()