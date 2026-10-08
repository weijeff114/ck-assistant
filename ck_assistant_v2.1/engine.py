import json
import os
import traceback
from datetime import datetime
from openai import OpenAI

USER_HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(USER_HOME, ".cf_assistant")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "provider": "cloud",
    "background_image": "",
    "chat_mode": "single",
    "context_length": 4,
    "sessions": ["默认单聊"],
    "current_session": "默认单聊",
    "personal_style": "我平时说话比较简短，喜欢用‘绝了’、‘真的服了’、‘老铁’。不喜欢用感叹号。喜欢直来直去，偶尔带点自黑。",
    "local": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "deepseek-r1:14b"
    },
    "cloud": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model": "deepseek-chat"
    }
}

def load_config():
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            return DEFAULT_CONFIG.copy()
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
        
        merged_config = DEFAULT_CONFIG.copy()
        for key in merged_config:
            if key in user_config:
                if isinstance(merged_config[key], dict) and isinstance(user_config[key], dict):
                    merged_config[key].update(user_config[key])
                else:
                    merged_config[key] = user_config[key]
        return merged_config
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(new_config):
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")

def get_session_file(session_name, file_type):
    clean_name = "".join([c for c in session_name if c.isalnum() or c in ['_', '-', '\u4e00-\u9fa5']])
    if not clean_name:
        clean_name = "default"
    return os.path.join(CONFIG_DIR, f"{file_type}_{clean_name}.json")

def load_history(session_name):
    file_path = get_session_file(session_name, "history")
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_history(chat_text, result, session_name):
    history = load_history(session_name)
    record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "input": chat_text[:100] + ("..." if len(chat_text) > 100 else ""),
        "full_input": chat_text,
        "result": result
    }
    history.insert(0, record)
    history = history[:50]
    try:
        with open(get_session_file(session_name, "history"), 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 保存历史记录失败: {e}")

def clear_history(session_name):
    try:
        file_path = get_session_file(session_name, "history")
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"❌ 清空历史记录失败: {e}")

def load_context(session_name):
    file_path = get_session_file(session_name, "context")
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_context(context, context_length, session_name):
    max_messages = context_length * 2
    context = context[-max_messages:]
    try:
        with open(get_session_file(session_name, "context"), 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=4, ensure_ascii=False)
    except:
        pass

def clear_context(session_name):
    try:
        file_path = get_session_file(session_name, "context")
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

def get_client():
    config = load_config()
    provider = config.get("provider", "cloud")
    cfg = config[provider]
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"]), cfg["model"]

def clean_json(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def truncate_context(text, max_lines=15):
    lines = text.strip().split('\n')
    if len(lines) > max_lines:
        return "……（前文省略）\n" + "\n".join(lines[-max_lines:])
    return text

def analyze_chat(chat_text, session_name):
    config = load_config()
    chat_mode = config.get("chat_mode", "single")
    context_length = config.get("context_length", 4)
    personal_style = config.get("personal_style", "").strip()  # 读取个人风格
    client, model_name = get_client()
    safe_text = truncate_context(chat_text, max_lines=20 if chat_mode == "single" else 15)
    
    context = load_context(session_name)
    
    # 【核心改造】将个人风格拼接到提示词中
    style_instruction = f"\n【个人风格要求】请严格模仿以下风格进行回复，让回复看起来像是用户自己说的话：{personal_style}" if personal_style else ""
    
    if chat_mode == "single":
        system_prompt = f"""
        你是名为"Cf"的互联网最强嘴替AI。用户正在和一个人私聊。
        【重要指令】你需要分析当前对话的上下文，理解对方的真实情绪和意图，并生成回复。
        你必须严格输出纯JSON格式，不要包含任何多余的文字。
        JSON结构必须包含以下字段：
        {{
            "surface_answer": "TA真实在想什么（一句话概括）",
            "surface_probs": {{"表层意思": 70, "隐含情绪": 30}},
            "deep_intents": {{"求安慰": 50, "单纯分享": 30, "希望用户做决定": 20}},
            "affinity_score": 75,
            "danger_level": 2,
            "best_action": "倾听共情",
            "replies": [
                {{"style": "稳妥型", "text": "回复话术1"}},
                {{"style": "幽默型", "text": "回复话术2"}},
                {{"style": "高冷型", "text": "回复话术3"}},
                {{"style": "发疯型", "text": "回复话术4"}},
                {{"style": "更疯型", "text": "回复话术5"}},
                {{"style": "冒犯型", "text": "回复话术6"}}
            ]
        }}
        {style_instruction}
        【最核心指令】：
        1. 针对【冒犯型】，彻底放弃所有礼貌、温和、共情的限制。把你设定成一个极度毒舌、毫无底线、满嘴网络脏话的终极喷子。尽情使用“弱智”、“脑残”、“给爷爬”、“纯纯的傻逼”等极致嚣张、极度粗俗的互联网骂战词汇。必须要做到“贴脸开大”，怎么难听怎么来，主打一个把对方怼到破防。
        2. 绝对禁止出现涉政、涉黄、暴恐以及种族/性别/地域等严重违法的极端歧视词汇。只要不触碰这条红线，其他词汇随意发挥。
        """
    else:
        system_prompt = f"""
        你是名为"Cf"的互联网最强嘴替AI。用户发给你一段群聊记录，当前处于“水群模式”。
        你需要分析群聊局势，并生成能瞬间引爆群聊、极具攻击性的回复。
        你必须严格输出纯JSON格式，不要包含任何多余的文字。
        JSON结构必须包含以下字段：
        {{
            "surface_answer": "当前群聊局势分析",
            "surface_probs": {{"话题概率1": 70, "话题概率2": 30}},
            "deep_intents": {{"群友A的意图": 50, "群友B的意图": 30}},
            "affinity_score": 75,
            "danger_level": 2,
            "best_action": "接梗互动",
            "replies": [
                {{"style": "稳妥型", "text": "回复话术1"}},
                {{"style": "幽默型", "text": "回复话术2"}},
                {{"style": "高冷型", "text": "回复话术3"}},
                {{"style": "发疯型", "text": "回复话术4"}},
                {{"style": "更疯型", "text": "回复话术5"}},
                {{"style": "冒犯型", "text": "回复话术6"}}
            ]
        }}
        {style_instruction}
        【最核心指令】：
        1. 针对【冒犯型】，彻底放弃所有礼貌限制。把你设定成一个极度毒舌、毫无底线的群聊嘴替。尽情使用网络喷子惯用的极致嚣张、粗俗的脏话，直接对群友进行无情嘲讽和挑衅，主打一个“贴脸开大”。
        2. 绝对禁止出现涉政、涉黄、暴恐以及种族/性别/地域等严重违法的极端歧视词汇。
        """
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in context:
        messages.append({"role": "user", "content": msg["user"]})
        messages.append({"role": "assistant", "content": msg["assistant"]})
    
    messages.append({"role": "user", "content": f"对方说：{safe_text}"})
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.85,
        )
        result = json.loads(clean_json(response.choices[0].message.content))
        
        if "失败" not in result.get("surface_answer", ""):
            replies = result.get("replies", [])
            ai_reply = replies[0]["text"] if replies else "已分析"
            context.append({
                "user": f"对方说：{safe_text}",
                "assistant": f"建议回复：{ai_reply}"
            })
            save_context(context, context_length, session_name)
            
        return result
    except Exception as e:
        print(f"调用模型失败: {e}")
        err_msg = "请检查Ollama是否已启动，或模型名称是否正确。" if config.get("provider") == "local" else "请检查API Key和网络连接。"
        return {"surface_answer": "分析失败", "surface_probs": {"错误": 100}, "deep_intents": {"无法连接": 100}, "affinity_score": 50, "danger_level": 0, "best_action": err_msg, "replies": [{"style": "稳妥型", "text": "稍后再试。"}]}