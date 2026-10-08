import sys
import pyperclip
import keyboard
import threading
import base64
import io
from PIL import ImageGrab, Image
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
    if provider == "campus" and not config["campus"]["api_key"]:
        window.show_status("⚠️ 校园模式未配置 API Key，正在打开设置...", is_error=True)
        open_settings()
        return

    chat_text = window.input_box.toPlainText().strip()
    image_base64 = None

    if window.current_image_base64:
        image_base64 = window.current_image_base64
    else:
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                window.set_image_preview(image_base64)
        except Exception as e:
            print(f"读取剪贴板图片失败: {e}")

    if not chat_text and not image_base64:
        chat_text = pyperclip.paste().strip()
    
    if not chat_text and not image_base64:
        window.show_status("⚠️ 请粘贴或输入聊天记录，或复制到剪贴板！", is_error=True)
        return
    
    mode_name = "云端API" if provider == "cloud" else ("校园API" if provider == "campus" else "本地Ollama")
    chat_mode_name = "单聊" if config.get("chat_mode") == "single" else "水群"
    context_turns = config.get("context_length", 4)
    unlimited = config.get("unlimited_memory", False)
    memory_desc = "无限记忆" if unlimited else f"{context_turns}轮记忆"
    
    input_type = "图片" if image_base64 else "文本"
    window.show_status(f"⏳ 【{session_name}】使用【{mode_name}】{chat_mode_name}模式（{memory_desc}）分析{input_type}...")
    
    window.update_signal.emit({"surface_answer": f"正在分析{input_type}...", "surface_probs": {}, "deep_intents": {}, "affinity_score": "...", "danger_level": "...", "best_action": "分析中", "replies": [], "persona_analysis": {}, "action_advice": ""})
    
    def run():
        result = analyze_chat(chat_text, session_name, image_base64)
        window.update_signal.emit(result)
        
        if "失败" not in result.get("surface_answer", "") and "检查" not in result.get("best_action", ""):
            save_history(chat_text or "[图片分析]", result, session_name)
            if window.is_history_open:
                window.refresh_history_list()
            window.show_status("✅ 分析完成！")
            window.clear_image()
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
print(" Cf 助手 v2.2 已启动！")
print(" 1. 支持风格克隆与无限记忆")
print(" 2. 支持截图视觉分析与群友画像")
print(" 3. 支持 云端/校园/本地 三通道切换")
print(" 4. 按 Ctrl+Shift+S 配置 API")
print(" 5. 按 Ctrl+Shift+Q 彻底退出")
print("====================================")

sys.exit(app.exec_())