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

is_analyzing = False

def open_settings():
    dialog = SettingsDialog(window)
    dialog.exec_()

def trigger_analysis():
    global is_analyzing
    if is_analyzing:
        window.show_status("⏳ 正在分析中，请稍候...", is_error=True)
        return

    config = load_config()
    provider_name = config.get("current_provider", "DeepSeek-官方")
    providers = config.get("custom_providers", {})
    
    if provider_name not in providers:
        window.show_status("⚠️ 当前 API 配置不存在，请点击 ⚙️ 重新添加！", is_error=True)
        open_settings()
        return
        
    cfg = providers[provider_name]
    if not cfg.get("base_url") or (not cfg.get("api_key") and "localhost" not in cfg.get("base_url", "") and "127.0.0.1" not in cfg.get("base_url", "")):
        window.show_status("⚠️ 当前 API 配置不完整，请点击 ⚙️ 补全地址或密钥！", is_error=True)
        open_settings()
        return

    session_name = window.session_combo.currentText()
    chat_text = window.input_box.toPlainText().strip()
    
    # 【v2.4 新增】读取心情和背景
    user_mood = window.mood_combo.currentText().strip()
    user_context = config.get("session_backgrounds", {}).get(session_name, "")
    
    image_base64 = None

    if window.current_image_base64:
        image_base64 = window.current_image_base64
    else:
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                img.thumbnail((800, 800))
                buffered = io.BytesIO()
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buffered, format="JPEG", quality=75)
                image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                window.set_image_preview(image_base64)
        except Exception as e:
            print(f"读取剪贴板图片失败: {e}")

    if not chat_text and not image_base64:
        chat_text = pyperclip.paste().strip()
    
    if not chat_text and not image_base64:
        window.show_status("⚠️ 请粘贴或输入聊天记录，或复制到剪贴板！", is_error=True)
        return
    
    chat_mode_name = "单聊" if config.get("chat_mode") == "single" else "水群"
    context_turns = config.get("context_length", 4)
    unlimited = config.get("unlimited_memory", False)
    memory_desc = "无限记忆" if unlimited else f"{context_turns}轮记忆"
    
    input_type = "图片" if image_base64 else "文本"
    window.show_status(f"⏳ 【{session_name}】心情({user_mood}) 分析{input_type}中...")
    
    window.update_signal.emit({"surface_answer": f"正在分析{input_type}...", "surface_probs": {}, "deep_intents": {}, "affinity_score": "...", "danger_level": "...", "best_action": "分析中", "replies": [], "persona_analysis": {}, "action_advice": ""})
    
    is_analyzing = True

    def run():
        global is_analyzing
        try:
            # 【v2.4 新增】传入 user_mood 和 user_context
            result = analyze_chat(chat_text, session_name, image_base64, user_mood, user_context)
            window.update_signal.emit(result)
            if "失败" not in result.get("surface_answer", "") and "检查" not in result.get("best_action", ""):
                save_history(chat_text or "[图片分析]", result, session_name)
                if window.is_history_open:
                    window.refresh_history_list()
                window.show_status("✅ 分析完成！")
                window.clear_image()
            else:
                window.show_error_dialog(result.get("best_action"))
        finally:
            is_analyzing = False
        
    threading.Thread(target=run).start()

def quit_app():
    app.quit()
    sys.exit()

keyboard.add_hotkey('ctrl+shift+j', trigger_analysis)
keyboard.add_hotkey('ctrl+shift+s', open_settings)
keyboard.add_hotkey('ctrl+shift+q', quit_app)

print("====================================")
print(" Cf 助手 v2.4 已启动！")
print(" 1. 支持心情注入与背景补充")
print(" 2. 支持截图视觉分析与群友画像")
print(" 3. 支持风格克隆与无限记忆")
print(" 4. 按 Ctrl+Shift+S 配置 API")
print(" 5. 按 Ctrl+Shift+Q 彻底退出")
print("====================================")

sys.exit(app.exec_())