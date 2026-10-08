import sys
import pyperclip
import keyboard
import threading
from PyQt5.QtWidgets import QApplication
from ui import CfWindow
from engine import analyze_chat

app = QApplication(sys.argv)
window = CfWindow()

def trigger_analysis():
    chat_text = pyperclip.paste()
    if not chat_text.strip():
        print("剪贴板为空，请先复制对方的聊天记录！")
        return
    
    print(f"Cf正在分析: {chat_text}")
    
    # 【核心修复】由于 keyboard 是在子线程触发的，这里也必须用信号，不能直接 update_data
    window.update_signal.emit({
        "surface_answer": "正在思考...",
        "surface_probs": {},
        "deep_intents": {},
        "affinity_score": "...",
        "danger_level": "...",
        "best_action": "分析中",
        "suggested_reply": "请稍候，Cf正在绞尽脑汁..."
    })
    
    def run():
        result = analyze_chat(chat_text)
        # 子线程算完后，继续用信号传回结果
        window.update_signal.emit(result)
        print("分析完成")
        
    threading.Thread(target=run).start()

# 绑定全局快捷键 Ctrl+Shift+J
keyboard.add_hotkey('ctrl+shift+j', trigger_analysis)

print("====================================")
print(" Cf · 高情商聊天助手已启动！")
print(" 操作说明：")
print(" 1. 复制对方发来的聊天记录 (Ctrl+C)")
print(" 2. 按下 Ctrl+Shift+J 获取分析建议")
print(" 3. 按 Ctrl+C 退出程序")
print("====================================")

sys.exit(app.exec_())