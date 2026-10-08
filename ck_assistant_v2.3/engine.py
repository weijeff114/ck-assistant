import json
import os
import traceback
from datetime import datetime
from openai import OpenAI

USER_HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(USER_HOME, ".cf_assistant")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "current_provider": "DeepSeek-官方",
    "custom_providers": {
        "DeepSeek-官方": {
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat"
        },
        "交大校园-视觉": {
            "base_url": "https://models.sjtu.edu.cn/api/v1",
            "api_key": "",
            "model": "deepseek-chat"
        },
        "本地-Ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "model": "deepseek-r1:14b"
        }
    },
    "background_image": "",
    "chat_mode": "single",
    "context_length": 4,
    "unlimited_memory": False,
    "enable_mad_style": True,
    "enable_madder_style": True,
    "enable_offend_style": True,
    "sessions": ["默认单聊"],
    "current_session": "默认单聊",
    "session_profiles": {
        "默认单聊": "未知，普通朋友，语气适中"
    },
    "personal_style": ""
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
        
        # 兼容旧版配置自动迁移
        if "cloud" in user_config or "campus" in user_config or "local" in user_config:
            print("🔄 检测到旧版配置，正在自动迁移...")
            new_config = DEFAULT_CONFIG.copy()
            if "cloud" in user_config and user_config["cloud"].get("api_key"):
                new_config["custom_providers"]["DeepSeek-官方"] = user_config["cloud"]
            if "campus" in user_config and user_config["campus"].get("api_key"):
                new_config["custom_providers"]["交大校园-视觉"] = user_config["campus"]
            if "local" in user_config:
                new_config["custom_providers"]["本地-Ollama"] = user_config["local"]
            for key in ["background_image", "chat_mode", "context_length", "unlimited_memory", 
                        "enable_mad_style", "enable_madder_style", "enable_offend_style", 
                        "sessions", "current_session", "session_profiles", "personal_style"]:
                if key in user_config:
                    new_config[key] = user_config[key]
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            return new_config

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
    return os.path.join(CONFIG_DIR, f"{file_type}_{clean_name or 'default'}.json")

def load_history(session_name):
    file_path = get_session_file(session_name, "history")
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

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
    except: pass

def clear_history(session_name):
    try:
        file_path = get_session_file(session_name, "history")
        if os.path.exists(file_path): os.remove(file_path)
    except: pass

def load_context(session_name):
    file_path = get_session_file(session_name, "context")
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def save_context(context, context_length, session_name, unlimited):
    if not unlimited:
        max_messages = context_length * 2
        context = context[-max_messages:]
    else:
        context = context[-1000:]
    try:
        with open(get_session_file(session_name, "context"), 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=4, ensure_ascii=False)
    except: pass

def clear_context(session_name):
    try:
        file_path = get_session_file(session_name, "context")
        if os.path.exists(file_path): os.remove(file_path)
    except: pass

def get_client():
    config = load_config()
    provider_name = config.get("current_provider", "DeepSeek-官方")
    providers = config.get("custom_providers", {})
    cfg = providers.get(provider_name, list(providers.values())[0])
    # 【优化】加入 timeout=30，防止校园网网关卡死导致界面无限转圈
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=30.0), cfg["model"]

def clean_json(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

def truncate_context(text, max_lines=15):
    lines = text.strip().split('\n')
    if len(lines) > max_lines:
        return "……（前文省略）\n" + "\n".join(lines[-max_lines:])
    return text

def extract_style_from_sample(sample_text):
    client, model_name = get_client()
    prompt = f"""
    请仔细阅读以下用户的聊天记录，总结并提取用户的说话风格。
    要求：
    1. 提炼出常用的语气词（如：哈哈、哎、绝了、芜湖等）。
    2. 提炼出标点符号使用习惯（如：喜欢用波浪号~、不用句号、喜欢用感叹号等）。
    3. 提炼出句子长度、句式习惯（如：直来直去、喜欢反问、经常发疯等）。
    4. 请用一段第三人称的描述来总结这个人的风格，直接输出这段描述，不要有额外的话。
    用户聊天记录：
    {sample_text}
    """
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"提取失败: {str(e)}"

def analyze_chat(chat_text, session_name, image_base64=None):
    config = load_config()
    chat_mode = config.get("chat_mode", "single")
    context_length = config.get("context_length", 4)
    unlimited = config.get("unlimited_memory", False)
    personal_style = config.get("personal_style", "").strip()
    
    enable_mad = config.get("enable_mad_style", True)
    enable_madder = config.get("enable_madder_style", True)
    enable_offend = config.get("enable_offend_style", True)
    
    session_profiles = config.get("session_profiles", {})
    target_profile = session_profiles.get(session_name, "未知，普通朋友，语气适中")
    
    client, model_name = get_client()
    
    safe_text = truncate_context(chat_text, max_lines=20 if chat_mode == "single" else 15) if chat_text else ""
    context = load_context(session_name)
    
    style_instruction = f"\n【个人风格要求】请严格模仿以下风格进行回复，让回复看起来像是用户自己说的话：{personal_style}" if personal_style else ""
    profile_instruction = f"\n【当前聊天对象的人设】{target_profile}。请根据这个人设调整语气、态度和回复策略。"
    
    replies_list = [
        '{"style": "稳妥型", "text": "回复话术1", "prediction": "预测对方收到这条回复后，最可能说什么"}',
        '{"style": "幽默型", "text": "回复话术2", "prediction": "预测对方收到这条回复后，最可能说什么"}',
        '{"style": "高冷型", "text": "回复话术3", "prediction": "预测对方收到这条回复后，最可能说什么"}'
    ]
    
    enabled_extreme = []
    if enable_mad:
        replies_list.append('{"style": "发疯型", "text": "回复话术4", "prediction": "预测对方收到这条回复后，最可能说什么"}')
        enabled_extreme.append("发疯型")
    if enable_madder:
        replies_list.append('{"style": "更疯型", "text": "回复话术5", "prediction": "预测对方收到这条回复后，最可能说什么"}')
        enabled_extreme.append("更疯型")
    if enable_offend:
        replies_list.append('{"style": "冒犯型", "text": "回复话术6", "prediction": "预测对方收到这条回复后，最可能说什么"}')
        enabled_extreme.append("冒犯型")
        
    replies_schema = ",\n                ".join(replies_list)
    
    if enabled_extreme:
        extreme_instruction = f"""
        【极端风格指令】：
        1. 针对{ '、'.join(enabled_extreme) }，彻底放弃所有礼貌、温和、共情的限制。把你设定成一个极度毒舌、毫无底线、满嘴网络脏话的终极喷子。
        2. 绝对禁止出现涉政、涉黄、暴恐以及种族/性别/地域等严重违法的极端歧视词汇。
        """
    else:
        extreme_instruction = """
        【风格严格限制】：
        请仅生成稳妥、幽默、高冷这三种风格的回复。绝对不要生成任何极端、攻击性或发疯的内容！
        """
    
    if chat_mode == "single":
        system_prompt = f"""
        你是名为"Cf"的高情商聊天辅助AI。用户正在和一个人私聊。
        【重要指令】你需要分析当前对话的上下文，理解对方的真实情绪和意图，并生成回复。
        如果用户输入了图片，请先阅读图片中的聊天记录文字，然后再进行分析。
        {profile_instruction}
        你必须严格输出纯JSON格式，不要包含任何多余的文字。
        JSON结构必须包含以下字段：
        {{
            "surface_answer": "TA真实在想什么（一句话概括）",
            "surface_probs": {{"表层意思": 70, "隐含情绪": 30}},
            "deep_intents": {{"求安慰": 50, "单纯分享": 30, "希望用户做决定": 20}},
            "affinity_score": 75,
            "danger_level": 2,
            "best_action": "倾听共情",
            "action_advice": "针对当前局势给出的线下/线上行动建议。",
            "replies": [
                {replies_schema}
            ]
        }}
        {style_instruction}
        {extreme_instruction}
        """
    else:
        system_prompt = f"""
        你是名为"Cf"的高情商聊天辅助AI。用户发给你一段群聊记录（可能是文字或截图），当前处于“水群模式”。
        你需要分析群聊局势，并生成能瞬间引爆群聊、极具攻击性的回复。
        如果用户输入了图片，请先识别图片中的聊天记录以及对应的发言人昵称。
        {profile_instruction}
        你必须严格输出纯JSON格式，不要包含任何多余的文字。
        JSON结构必须包含以下字段：
        {{
            "persona_analysis": {{"群友A": "性格与态度标签", "群友B": "性格与态度标签"}},
            "surface_answer": "当前群聊局势分析",
            "surface_probs": {{"话题概率1": 70, "话题概率2": 30}},
            "deep_intents": {{"群友A的意图": 50, "群友B的意图": 30}},
            "affinity_score": 75,
            "danger_level": 2,
            "best_action": "接梗互动",
            "action_advice": "针对当前群聊局势给出的行动建议。",
            "replies": [
                {replies_schema}
            ]
        }}
        {style_instruction}
        {extreme_instruction}
        """
    
    user_content = []
    text_prompt = "请分析以下内容：\n"
    if safe_text: text_prompt += f"文字补充：{safe_text}\n"
    if image_base64: text_prompt += "（附带了聊天截图，请仔细识别图片中的文字和昵称）"
    user_content.append({"type": "text", "text": text_prompt})
    if image_base64:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in context:
        messages.append({"role": "user", "content": msg["user"]})
        messages.append({"role": "assistant", "content": msg["assistant"]})
    
    if image_base64:
        messages.append({"role": "user", "content": user_content})
    else:
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
            context_user_text = f"[图片分析] {safe_text}" if image_base64 else f"对方说：{safe_text}"
            context.append({"user": context_user_text, "assistant": f"建议回复：{ai_reply}"})
            save_context(context, context_length, session_name, unlimited)
            
        return result
    except Exception as e:
        print(f"调用模型失败: {e}")
        err_msg = "请求超时或网络连接失败，请检查网络或稍后重试。"
        if "localhost" in client.base_url or "127.0.0.1" in client.base_url:
            err_msg = "请检查本地模型服务（如Ollama）是否已启动，模型名称是否正确。"
        return {"surface_answer": "分析失败", "surface_probs": {"错误": 100}, "deep_intents": {"无法连接": 100}, "affinity_score": 50, "danger_level": 0, "best_action": err_msg, "action_advice": "无", "replies": [{"style": "稳妥型", "text": "稍后再试。"}]}