# Cf 助手 / ck-assistant
# Copyright (c) 2026 Wei Qiguang (weijeff114)
# SPDX-License-Identifier: GPL-3.0-only

# ================= 【终极护盾】强制屏蔽终端崩溃 =================
import sys
from _debug_logger import install_global_logging
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

class SafeWriter:
    """安全的输出流，防止终端不支持中文导致崩溃"""
    def __init__(self, filename):
        self.f = open(filename, 'a', encoding='utf-8')
    def write(self, text):
        try:
            if text.strip():
                self.f.write(text + "\n")
                self.f.flush()
        except Exception:
            pass
    def flush(self):
        try:
            self.f.flush()
        except Exception:
            pass
    @property
    def encoding(self):
        return 'utf-8'

# 将 print 的内容写入 cf_app_log.txt，不再输出到终端
sys.stdout = SafeWriter("cf_app_log.txt")
sys.stderr = SafeWriter("cf_app_log.txt")
# ===============================================================

import pyperclip
import keyboard
import threading
import base64
import io
from PIL import ImageGrab, Image
from PyQt5.QtWidgets import QApplication, QInputDialog
from PyQt5.QtCore import QObject, pyqtSignal
from ui import CfWindow, SettingsDialog
from engine import analyze_chat, load_config, save_history, clear_context, detect_missing_context

class ThreadBridge(QObject):
    open_settings = pyqtSignal()
    trigger_analysis = pyqtSignal()
    ask_context = pyqtSignal(str)
    update_ui = pyqtSignal(dict)

bridge = ThreadBridge()

install_global_logging()
app = QApplication(sys.argv)
window = CfWindow()
window.show()

is_analyzing = False
current_chat_text = "" 
current_image_base64 = None

def open_settings():
    dialog = SettingsDialog(window)
    dialog.exec_()

def handle_ask_context(question):
    global is_analyzing
    text, ok = QInputDialog.getText(window, "补充情报", 
        f"🤔 军师提问：{question}\n\n请补充简短背景（直接回车可跳过）：")
    additional_info = text.strip() if ok and text.strip() else ""
    window.show_status("⏳ 情报已补充，正在生成回复...")
    start_stage2(additional_info)

def update_ui_after_analysis(result):
    global current_chat_text, is_analyzing
    window.update_data(result)
    if "失败" not in result.get("surface_answer", "") and "检查" not in result.get("best_action", ""):
        save_history(current_chat_text, result, window.session_combo.currentText())
        if window.is_history_open:
            window.refresh_history_list()
        window.show_status("✅ 分析完成！")
        window.clear_image()
    else:
        window.show_error_dialog(result.get("best_action", "未知错误"))
    is_analyzing = False

def start_stage2(additional_info):
    global is_analyzing, current_chat_text, current_image_base64
    config = load_config()
    session_name = window.session_combo.currentText()
    user_mood = window.mood_combo.currentText().strip()
    user_context = config.get("session_backgrounds", {}).get(session_name, "")

    def stage2_run():
        global is_analyzing
        try:
            result = analyze_chat(current_chat_text, session_name, current_image_base64, 
                                  user_mood, user_context, additional_info, feedback="")
            bridge.update_ui.emit(result)
        except Exception as e:
            bridge.update_ui.emit({"surface_answer": "分析失败", "replies": [], "best_action": str(e)})
        finally:
            is_analyzing = False

    threading.Thread(target=stage2_run).start()

def trigger_analysis():
    try:
        _trigger_analysis_impl()
    except Exception:
        import traceback
        try:
            from _debug_logger import log
            log('=== trigger_analysis 完整traceback ===', level='critical')
            log(traceback.format_exc(), level='critical')
        except Exception:
            pass
        window.show_status("分析异常，详情见 debug_log.txt", is_error=True)


def _trigger_analysis_impl():
    global is_analyzing, current_chat_image_base64
    try:
        from _debug_logger import log
        log('trigger_analysis_impl 被调用', level='debug')
        log('attempt1', level='debug')
        # 调用原实现
        _impl_body()
    except Exception:
        import traceback
        try:
            from _debug_logger import log
            log(traceback.format_exc(), level='critical')
        except Exception:
            pass
def _impl_body():
    global is_analyzing, current_chat_text, current_image_base64
    if is_analyzing:
        window.show_status("⏳ 正在分析中，请稍候...", is_error=True)
        return

    config = load_config()
    provider_name = config.get("current_provider", "DeepSeek-官方")
    providers = config.get("custom_providers", {})
    
    if provider_name not in providers:
        window.show_status("⚠️ API 配置不存在，请点击 ⚙️ 重新添加！", is_error=True)
        return
        
    cfg = providers[provider_name]
    if not cfg.get("base_url") or (not cfg.get("api_key") and "localhost" not in cfg.get("base_url", "") and "127.0.0.1" not in cfg.get("base_url", "")):
        window.show_status("⚠️ API 配置不完整，请点击 ⚙️ 补全地址或密钥！", is_error=True)
        return

    session_name = window.session_combo.currentText()
    chat_text = window.input_box.toPlainText().strip()
    
    current_image_base64 = None
    if window.current_image_base64:
        current_image_base64 = window.current_image_base64
    else:
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                img.thumbnail((800, 800))
                buffered = io.BytesIO()
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(buffered, format="JPEG", quality=75)
                current_image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                window.set_image_preview(current_image_base64)
        except Exception as e:
            pass

    if not chat_text and not current_image_base64:
        chat_text = pyperclip.paste().strip()
    
    if not chat_text and not current_image_base64:
        window.show_status("⚠️ 请粘贴或输入聊天记录，或复制到剪贴板！", is_error=True)
        return

    current_chat_text = chat_text or "[图片分析]"
    user_mood = window.mood_combo.currentText().strip()
    
    is_analyzing = True
    window.show_status("🧠 军师正在评估局势...")

    def stage1_run():
        try:
            check_result = detect_missing_context(current_chat_text, session_name)
            if check_result.get("need_context"):
                bridge.ask_context.emit(check_result['question'])
            else:
                start_stage2("")
        except Exception as e:
            try:
                import traceback as _tb
                from _debug_logger import log
                log('=== detect_missing_context 异常(完整栈) ===', level='critical')
                log(_tb.format_exc(), level='critical')
            except Exception:
                pass
            start_stage2("")

    threading.Thread(target=stage1_run).start()

def handle_regenerate(reason):
    """🔄 重新生成：基于上次分析的聊天记录/图片 + 用户反馈，重跑一次分析。"""
    global is_analyzing
    if is_analyzing:
        window.show_status("⏳ 正在分析中，请稍候...", is_error=True)
        return
    if not current_chat_text and not current_image_base64:
        window.show_status("⚠️ 请先进行首次分析，再使用重新生成！", is_error=True)
        return

    is_analyzing = True
    window.show_status("🧠 正在根据您的反馈重写...")

    def regen_run():
        global is_analyzing
        try:
            config = load_config()
            session_name = window.session_combo.currentText()
            user_mood = window.mood_combo.currentText().strip()
            user_context = config.get("session_backgrounds", {}).get(session_name, "")

            # 复用上次分析的聊天记录和图片，只替换 feedback
            result = analyze_chat(current_chat_text, session_name, current_image_base64,
                                  user_mood, user_context, additional_info="", feedback=reason)
            bridge.update_ui.emit(result)
        except Exception as e:
            bridge.update_ui.emit({"surface_answer": "重写失败", "replies": [],
                                   "best_action": "重写时出错：" + str(e)})
        finally:
            is_analyzing = False

    threading.Thread(target=regen_run, daemon=True).start()

window.regenerate_requested.connect(handle_regenerate)
window.analyze_requested.connect(trigger_analysis)
bridge.open_settings.connect(open_settings)
bridge.trigger_analysis.connect(trigger_analysis)
bridge.ask_context.connect(handle_ask_context)
bridge.update_ui.connect(update_ui_after_analysis)

def quit_app():
    app.quit()
    sys.exit()

keyboard.add_hotkey('ctrl+shift+j', lambda: bridge.trigger_analysis.emit())
keyboard.add_hotkey('ctrl+shift+s', lambda: bridge.open_settings.emit())
keyboard.add_hotkey('ctrl+shift+q', quit_app)

sys.exit(app.exec_())
