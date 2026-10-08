import sys
import pyperclip
import keyboard
import threading
from PyQt5.QtWidgets import QApplication
from ui import CfWindow, SettingsDialog
from engine import analyze_chat, load_config, save_history, clear_context

app = QApplication(sys.argv)
window = CfWindow()
window.show()
window.analyze_requested.connect(lambda: trigger_analysis())

def open_settings():
    dialog = SettingsDialog(window)
    dialog.exec_()

def clear_memory():
    session_name = window.session_combo.currentText()
    clear_context(session_name)
    window.show_status(f"🧠 会话【{session_name}】的上下文记忆已清空")

window.btn_clear_context.clicked.connect(clear_memory)

def trigger_analysis():
    config = load_config()
    provider = config.get("provider", "cloud")
    session_name = window.session_combo.currentText()
    
    if provider == "cloud" and not config["cloud"]["api_key"]:
        window.show_status("⚠️ 云端模式未配置 API Key，正在打开设置...", is_error=True)
        open_settings()
        return

    chat_text = window.input_box.toPlainText().strip()
    if not chat_text:
        chat_text = pyperclip.paste().strip()
    
    if not chat_text:
        window.show_status("⚠️ 请粘贴或输入聊天记录，或复制到剪贴板！", is_error=True)
        return
    
    mode_name = "云端API" if provider == "cloud" else "本地Ollama"
    chat_mode_name = "单聊" if config.get("chat_mode") == "single" else "水群"
    context_turns = config.get("context_length", 4)
    window.show_status(f"⏳ 【{session_name}】使用【{mode_name}】{chat_mode_name}模式（{context_turns}轮记忆）分析...")
    
    window.update_signal.emit({"surface_answer": "正在思考...", "surface_probs": {}, "deep_intents": {}, "affinity_score": "...", "danger_level": "...", "best_action": "分析中", "replies": []})
    
    def run():
        result = analyze_chat(chat_text, session_name)
        window.update_signal.emit(result)
        
        if "失败" not in result.get("surface_answer", "") and "检查" not in result.get("best_action", ""):
            save_history(chat_text, result, session_name)
            if window.is_history_open:
                window.refresh_history_list()
            window.show_status("✅ 分析完成！")
        else:
            window.show_error_dialog(result.get("best_action"))
        
    threading.Thread(target=run).start()

def quit_app():
    app.quit()
    sys.exit()

keyboard.add_hotkey('ctrl+shift+j', trigger_analysis)
keyboard.add_hotkey('ctrl+shift+s', open_settings)
keyboard.add_hotkey('ctrl+shift+q', quit_app)

print("====================================")
print(" Cf 助手 v2 已启动！")
print(" 1. 支持多会话独立记忆与历史")
print(" 2. 支持个人风格模仿")
print(" 3. 按 Ctrl+Shift+S 配置 API")
print(" 4. 按 Ctrl+Shift+Q 彻底退出")
print("====================================")

sys.exit(app.exec_())