import sys
import io
import json
import os
import traceback
import time
import html as _html
import re as _re
from datetime import datetime
from openai import OpenAI
import httpx as _httpx

from engine_config import (
    USER_HOME, CONFIG_DIR, CONFIG_FILE, DEFAULT_CONFIG,
    load_config, save_config, get_session_file, backup_corrupt_file,
)

def load_history(session_name):
    file_path = get_session_file(session_name, "history")
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception as e:
        backup_corrupt_file(file_path)
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
    except Exception as e:
        backup_corrupt_file(file_path)
        return []

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

# =========================================================
# 【待办1】多世界书（Multi-Lorebook）系统
# 每个世界书（知识包）是一个独立的 JSON 文件,包含主题介绍 + 词条列表
# =========================================================

def get_lorebook_dir():
    """知识包存储目录。"""
    d = os.path.join(CONFIG_DIR, "lorebooks")
    try:
        os.makedirs(d, exist_ok=True)
    except: pass
    return d

def get_lorebook_path(book_name):
    return os.path.join(get_lorebook_dir(), f"{book_name or '默认'}.json")

def load_lorebook(book_name="默认"):
    """读取指定知识包。文件不存在返回空结构。"""
    p = get_lorebook_path(book_name)
    if not os.path.exists(p):
        return {"name": book_name, "description": "", "terms": {}}
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"name": book_name, "description": "", "terms": {}}
        data.setdefault("name", book_name)
        data.setdefault("description", "")
        data.setdefault("terms", {})
        return data
    except Exception:
        return {"name": book_name, "description": "", "terms": {}}

def save_lorebook(data):
    """保存知识包。"""
    try:
        p = get_lorebook_path(data.get("name", "默认"))
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def list_lorebooks():
    """列出所有知识包名。"""
    d = get_lorebook_dir()
    result = ["默认"]
    try:
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                result.append(fn[:-5])
    except Exception:
        pass
    return sorted(set(result))

def add_lorebook_term(book_name, term, content):
    """向知识包添加一个词条。"""
    data = load_lorebook(book_name)
    data["terms"][term] = content
    return save_lorebook(data)

def remove_lorebook_term(book_name, term):
    data = load_lorebook(book_name)
    if term in data["terms"]:
        del data["terms"][term]
    return save_lorebook(data)

def delete_lorebook(book_name):
    try:
        p = get_lorebook_path(book_name)
        if os.path.exists(p):
            os.remove(p)
        return True
    except Exception:
        return False

def auto_write_lorebook(book_name, chat_history, base_description=""):
    """【待办2】AI 自动写书：让模型根据聊天记录自动生成知识包。"""
    client, model_name = get_client()
    history_text = "\n".join(chat_history[-20:]) if chat_history else "（无聊天记录）"
    prompt = f"""请阅读以下聊天记录,提取里面反复出现的专有名词,人物关系,事件背景等关键设定,
整理成一本书的格式。请严格输出纯JSON,结构为：
{{"name": "{book_name}", "description": "这本书的整体世界观/背景一句话概括", "terms": {{"名词1": "解释", "名词2": "解释"}}}}

{base_description_with_guard(base_description)}

聊天记录：
{history_text}"""
    try:
        response = client.chat.completions.create(
            model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.3,
        )
        cleaned = clean_json(response.choices[0].message.content)
        data = json.loads(cleaned) if cleaned else {}
        if isinstance(data, dict):
            data["name"] = book_name
            if save_lorebook(data):
                return data
        return {"name": book_name, "description": "自动生成失败,请手动补全", "terms": {}}
    except Exception as e:
        return {"name": book_name, "description": f"自动生成失败: {e}", "terms": {}}

def base_description_with_guard(desc=""):
    """辅助函数：自动写书时若提供了背景描述则拼入提示,未提供则留空。"""
    if desc and desc.strip():
        return f"背景补充（作者提供）：{desc.strip()}"
    return "（无额外背景补充）"

def search_meme(term, max_results=3):
    """【待办3】联网查梗：使用 DuckDuckGo 搜索指定梗词条。"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(term, max_results=max_results))
        return [r.get("title", "") + "\n" + r.get("href", "") for r in results]
    except Exception as e:
        return [f"查梗失败: {e}"]


def load_saves(session_name):
    file_path = get_session_file(session_name, "saves")
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception as e:
        backup_corrupt_file(file_path)
        return []

def create_save(session_name, note, scene_data):
    saves = load_saves(session_name)
    save_id = str(int(time.time() * 1000))
    record = {"id": save_id, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "note": note or "未命名存档", "scene": scene_data}
    saves.insert(0, record)
    saves = saves[:100]
    try:
        with open(get_session_file(session_name, "saves"), 'w', encoding='utf-8') as f:
            json.dump(saves, f, indent=4, ensure_ascii=False)
        return save_id
    except: return None

def delete_save(session_name, save_id):
    saves = load_saves(session_name)
    saves = [s for s in saves if s.get("id") != save_id]
    try:
        with open(get_session_file(session_name, "saves"), 'w', encoding='utf-8') as f:
            json.dump(saves, f, indent=4, ensure_ascii=False)
        return True
    except: return False

def clear_saves(session_name):
    try:
        file_path = get_session_file(session_name, "saves")
        if os.path.exists(file_path): os.remove(file_path)
    except: pass

def get_client():
    config = load_config()
    provider_name = config.get("current_provider", "DeepSeek-官方")
    providers = config.get("custom_providers", {})
    cfg = providers.get(provider_name, list(providers.values())[0])
    
    base_url = _re.sub(r"\s+", "", str(cfg.get("base_url", "")))
    api_key = str(cfg.get("api_key", "")).strip()
    model_name = str(cfg.get("model", "")).strip()
    
    if not base_url.startswith("http"):
        raise ValueError(f"API 地址格式错误：'{base_url}' 必须以 http:// 或 https:// 开头！")
    
    try:
        client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=30.0,
        http_client=_httpx.Client(trust_env=False, timeout=30.0),
        )
        return client, model_name
    except Exception as e:
        raise ValueError(f"初始化 API 客户端失败：{e}")

def clean_json(text):
    """提取并清理一段可能包裹在 markdown 或解释文字中的 JSON 字符串。

    处理常见问题：
    - 代码块包裹（```json ... ``` / ``` ... ```）
    - 前后有解释文字（定位第一个 { 和最后一个 }）
    - 空内容 / 全空白 → 返回 ""
    返回内容可直接交给 json.loads。若无法定位到合法 JSON 边界,返回 ""。
    """
    if text is None:
        return ""
    text = text.strip()
    if not text:
        return ""
    # 剥离 markdown 代码块围栏（```json / ```jsonl / ``` 等,含 \r\n 或 \n 结尾）
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        # 去掉首行围栏（可能带语言标记）
        lines = lines[1:]
        # 去掉末尾围栏行
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not text:
        return ""
    # 兜底：定位第一个 { 与最后一个 },剥掉两侧解释文字
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    # 连大括号都找不到,说明完全不是 JSON
    return ""

def truncate_context(text, max_lines=15):
    lines = text.strip().split('\n')
    if len(lines) > max_lines:
        return "……（前文省略）\n" + "\n".join(lines[-max_lines:])
    return text

def extract_style_from_sample(sample_text):
    client, model_name = get_client()
    prompt = f"请仔细阅读以下用户的聊天记录,总结并提取用户的说话风格。直接输出风格描述,不要有额外的话。\n用户聊天记录：\n{sample_text}"
    try:
        response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.3)
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"提取失败: {str(e)}"

def detect_missing_context(chat_text, session_name):
    config = load_config()
    context = load_context(session_name)
    safe_text = truncate_context(chat_text, max_lines=10)
    
    client, model_name = get_client()
    
    system_prompt = """
    你是一个聊天辅助AI的“前哨”。你的唯一任务是判断：如果不知道某个背景信息,是否能回复对方的这句话。
    你必须严格输出纯JSON格式：
    {
        "need_context": true/false,
        "question": "如果需要背景,你想问用户什么？（例如：对方说的'那个东西'是指什么？）"
    }
    注意：只有当你觉得“完全无法理解对方在指什么”或者“极易答非所问”时,才填 need_context = true。
    对于普通的日常问候,情绪发泄,或者不需要特定背景的对话,need_context 一律填 false。
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in context[-4:]:
        messages.append({"role": "user", "content": msg["user"]})
        messages.append({"role": "assistant", "content": msg["assistant"]})
    messages.append({"role": "user", "content": f"对方说：{safe_text}"})
    
    try:
        response = client.chat.completions.create(
            model=model_name, messages=messages, temperature=0.1,
        )
        cleaned = clean_json(response.choices[0].message.content)
        if not cleaned:
            # 模型未返回任何可解析内容,不弹窗,直接跳过追问
            print("⚠️ 前哨未返回可解析内容,跳过追问")
            return {"need_context": False, "question": ""}
        return json.loads(cleaned)
    except Exception as e:
        print(f"检测上下文失败: {e}")
        # 返回非空 question,前端弹窗不会因空字符串卡死
        return {"need_context": False, "question": "未可读取,请直接回复。"}

def parse_plain_text_replies(raw_text):
    # 【宽容版纯文本提取法】第 1 级：题目指定正则；第 2 级：按行分割兜底
    import re as _re
    text = (raw_text or "").strip()

    _STYLES = ("稳妥型", "幽默型", "高冷型", "发疯型", "更疯型", "冒犯型", "开心型", "踏实型")

    _META_WORDS = (
        "好感","危险", "等级", "程度", "上升", "下降","风险","行动","目标","备注","预测","分数","评分","指数","建议","结论","摘要","总结"
    )

    def _is_meta_label(name):
        if not name:
            return True
        if name.endswith("型") and name not in ("稳妥型", "幽默型", "高冷型", "发疯型", "更疯型", "冒犯型", "开心型", "踏实型"):
            return True
        for w in _META_WORDS:
            if w in name:
                return True
        return False
    matches = _re.findall(r"【([^】]+)】\s*([\s\S]*?)(?=【|\Z)", text)
    replies = []
    for style, content in matches:
        content = content.strip()
        s = style.strip()
        if s and content and not _is_meta_label(s):
            replies.append({"style": s, "text": content, "prediction": "（当前API未提供预测）"})
    if not replies:
        known = ("稳妥型", "幽默型", "高冷型", "发疯型", "更疯型", "冒犯型")
        lines = [ln.strip() for ln in _re.split(r"\n+", text) if ln.strip()]
        cur, buf = None, []
        for ln in lines:
            if ln.startswith("【") and "】" in ln:
                head, _, rest = ln.partition("】")
                sty = head.strip("【* ")
                if any(k == sty or k in sty or sty in k for k in known) and not _is_meta_label(sty):
                    if cur and buf:
                        replies.append({"style": cur, "text": " ".join(buf), "prediction": "（当前API未提供预测）"})
                    cur = sty
                    buf = [rest.strip()] if rest.strip() else []
            elif cur is not None:
                buf.append(ln)
        if cur and buf:
            replies.append({"style": cur, "text": " ".join(buf), "prediction": "（当前API未提供预测）"})
    if not replies:
        # 【最终双保险·多段切分】不在清理后的纯文本里发明JSON,而是保留原文的多段行,
        # 按空行/序号/符号切分成多个独立候选回复,确保多风格不丢失。
        segs = [ln.strip() for ln in _re.split(r"[\n\r]+|(?=\d+\.|[-*+] )", text) if ln.strip()]
        if len(segs) >= 2:
            replies = [{"style": "未标注风格（分段兜底）", "text": seg, "prediction": "（当前API未提供预测）"} for seg in segs]
        else:
            replies = [{"style": "稳妥型", "text": text, "prediction": "（未解析到明确风格）"}]

    return replies








def analyze_chat(chat_text, session_name, image_base64=None, user_mood="平静", user_context="", additional_info="", feedback=""):
    config = load_config()
    chat_mode = config.get("chat_mode", "single")
    context_length = config.get("context_length", 4)
    unlimited = config.get("unlimited_memory", False)
    personal_style = config.get("personal_style", "").strip()
    
    enable_mad = config.get("enable_mad_style", True)
    enable_madder = config.get("enable_madder_style", True)
    enable_offend = config.get("enable_offend_style", True)
    
    session_profiles = config.get("session_profiles", {})
    target_profile = session_profiles.get(session_name, "未知,普通朋友,语气适中")
    
    client, model_name = get_client()
    safe_text = truncate_context(chat_text, max_lines=20 if chat_mode == "single" else 15) if chat_text else ""
    context = load_context(session_name)
    
    style_instruction = f"\n【个人风格要求】请严格模仿以下风格进行回复：{personal_style}" if personal_style else ""
    profile_instruction = f"\n【当前聊天对象的人设】{target_profile}。请根据这个人设调整语气,态度和回复策略。"
    
    mood_instruction = ""
    if user_mood and user_mood.strip() and user_mood.strip() != "平静":
        mood_instruction = f"\n【用户当前心情】用户此刻的心情是：{user_mood.strip()}。请让生成的回复体现出强烈的情绪色彩,符合这个心情！"
    
    background_instruction = ""
    if user_context and user_context.strip():
        background_instruction = f"\n【前情提要/背景补充】用户提供了以下背景信息：{user_context.strip()}。请务必结合这些背景信息来理解当前的对话。"
    
    extra_info_instruction = ""
    if additional_info:
        extra_info_instruction = f"\n【用户补充的关键情报】{additional_info}。请务必把这个情报作为回复的前提！"

    feedback_instruction = ""
    if feedback and feedback.strip():
        feedback_instruction = f"""
        \n【用户对上一次生成的选项不满意！】
        用户的抱怨是：{feedback.strip()}
        请你务必避免之前的问题（比如太官方,太长,太敷衍）,重新生成一批全新的回复选项。
        """

    replies_list = [
        '{"style": "稳妥型", "text": "回复话术1", "prediction": "预测对方收到这条回复后,最可能说什么"}',
        '{"style": "幽默型", "text": "回复话术2", "prediction": "预测对方收到这条回复后,最可能说什么"}',
        '{"style": "高冷型", "text": "回复话术3", "prediction": "预测对方收到这条回复后,最可能说什么"}'
    ]
    enabled_extreme = []
    if enable_mad:
        replies_list.append('{"style": "发疯型", "text": "回复话术4", "prediction": "预测对方收到这条回复后,最可能说什么"}')
        enabled_extreme.append("发疯型")
    if enable_madder:
        replies_list.append('{"style": "更疯型", "text": "回复话术5", "prediction": "预测对方收到这条回复后,最可能说什么"}')
        enabled_extreme.append("更疯型")
    if enable_offend:
        replies_list.append('{"style": "冒犯型", "text": "回复话术6", "prediction": "预测对方收到这条回复后,最可能说什么"}')
        enabled_extreme.append("冒犯型")
    replies_schema = ",\n                ".join(replies_list)
    
    if enabled_extreme:
        extreme_instruction = f"【极端风格指令】针对{ ','.join(enabled_extreme) },彻底放弃所有礼貌限制。绝对禁止出现涉政,涉黄,暴恐等严重违法的极端歧视词汇。"
    else:
        extreme_instruction = "【风格严格限制】请仅生成稳妥,幽默,高冷这三种风格的回复。"

    if chat_mode == "single":
        system_prompt = f"""
        你是名为"Cf"的高情商聊天辅助AI。用户正在和一个人私聊。
        {profile_instruction}
        {background_instruction}
        {mood_instruction}
        {extra_info_instruction}
        {feedback_instruction}
        你必须严格输出纯JSON格式,不要包含任何多余的文字。
        JSON结构必须包含以下字段：
        {{
            "surface_answer": "TA真实在想什么（一句话概括）",
            "surface_probs": {{"表层意思": 70, "隐含情绪": 30}},
            "deep_intents": {{"求安慰": 50, "单纯分享": 30, "希望用户做决定": 20}},
            "affinity_score": 75,
            "danger_level": 2,
            "best_action": "倾听共情",
            "action_advice": "针对当前局势给出的线下/线上行动建议。",
            "replies": [ {replies_schema} ]
        }}
        {style_instruction}
        {extreme_instruction}

        【备用输出格式】(重要！)如果你无法输出JSON,请严格按以下纯文本格式输出（禁止使用markdown加粗,禁止输出任何其他解释或JSON前缀说明）：
        【稳妥型】<稳妥风格的回复>
        【幽默型】<幽默风格的回复>
        【高冷型】<高冷风格的回复>
        (如果开启了其他风格：发疯型,更疯型,冒犯型,·要按【风格X】这样的格式追加输出)
        """
    else:
        system_prompt = f"""
        你是名为"Cf"的高情商聊天辅助AI。当前处于“水群模式”。
        {profile_instruction}
        {background_instruction}
        {mood_instruction}
        {extra_info_instruction}
        {feedback_instruction}
        你必须严格输出纯JSON格式,不要包含任何多余的文字。
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
            "replies": [ {replies_schema} ]
        }}
        {style_instruction}
        {extreme_instruction}

        【备用输出格式】(重要！)如果你无法输出JSON,请严格按以下纯文本格式输出（禁止使用markdown加粗,禁止输出任何其他解释或JSON前缀说明）：
        【稳妥型】<稳妥风格的回复>
        【幽默型】<幽默风格的回复>
        【高冷型】<高冷风格的回复>
        (如果开启了其他风格：发疯型,更疯型,冒犯型,·要按【风格X】这样的格式追加输出)
        """
    
    user_content = []
    text_prompt = "请分析以下内容：\n"
    if safe_text: text_prompt += f"文字补充：{safe_text}\n"
    if image_base64: text_prompt += "（附带了聊天截图）"
    user_content.append({"type": "text", "text": text_prompt})
    if image_base64:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
    
    # ===== 【待办功能一：多世界书+联网查梗 注入】=====
    try:
        sel_books = config.get("selected_lorebooks", [])
        if sel_books:
            book_parts = []
            for bn in sel_books:
                btxt = lorebook_prompt_for(bn)
                if btxt:
                    book_parts.append("《" + bn + "》\n" + btxt)
            if book_parts:
                system_prompt += "\n\n【世界书设定】（请将此文件中的设定视为不可违背的事实来帮助理解对话上下文）\n" + "\n\n".join(book_parts)

        if config.get("enable_web_search", False):
            system_prompt += (
                "\n\n【联网查梗】网络搜索已启用。若对话中出现你不确定的网络梗,热点事件或生僻词,"
                "请基于知识推测其含义并在回复中注明推测。若确实无法获取外部信息,请礼貌说明。"
            )
    except Exception as e:
        print(f"⚠️ 注入世界书/查梗失败: {e}")

    messages = [{"role": "system", "content": system_prompt}]
    for msg in context:
        # 防御：context 消息字段可能缺失,跳过非法条目
        u = msg.get("user") if isinstance(msg, dict) else None
        a = msg.get("assistant") if isinstance(msg, dict) else None
        if u: messages.append({"role": "user", "content": u})
        if a: messages.append({"role": "assistant", "content": a})
    
    if image_base64:
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": f"对方说：{safe_text}"})
    
    try:
        response = None
        for _attempt in range(2):
            try:
                response = client.chat.completions.create(model=model_name, messages=messages, temperature=0.85)
                break
            except Exception as _exc:
                if _attempt == 1:
                    raise
                import time as _t
                _t.sleep(1)
        raw_content = response.choices[0].message.content
        try:
            result = json.loads(clean_json(raw_content))
            # 【增强兜底】即使 JSON 解析“成功”,若 replies 不是含多个元素的列表,视为伪 JSON,
            # 强制降级为纯文本标签提取,避免出现“只有单个风格”的异常。
            _replies = result.get("replies") if isinstance(result, dict) else None
            if not (isinstance(_replies, list) and len(_replies) >= 2):
                replies = parse_plain_text_replies(raw_content)
                result = {
                    "surface_answer": "API返回了纯文本（已成功提取多风格）",
                    "surface_probs": {"纯文本模式": 100},
                    "deep_intents": {"闲聊": 100},
                    "affinity_score": 50,
                    "danger_level": 0,
                    "best_action": "倾听",
                    "action_advice": "学校API不支持格式化,以下为AI原话提取的多风格回复。",
                    "replies": replies
                    }
                result["_downgraded"] = True
        except json.JSONDecodeError:
            # 【核心降级方案】纯文本标签提取法：把标签文本解析成多风格回复
            replies = parse_plain_text_replies(raw_content)
            result = {
                "surface_answer": "API返回了纯文本（已成功提取多风格）",
                "surface_probs": {"纯文本模式": 100},
                "deep_intents": {"闲聊": 100},
                "affinity_score": 50,
                "danger_level": 0,
                "best_action": "倾听",
                "action_advice": "学校API不支持格式化,以下为AI原话提取的多风格回复。",
                "replies": replies
                }
            result["_downgraded"] = True
        if "失败" not in result.get("surface_answer", "") and not feedback and not result.get("_downgraded", False):
            replies = result.get("replies", [])
            # 安全取值：AI 可能返回非法格式（缺 text 字段,或 list 里是非 dict 等）
            ai_reply = "已分析"
            if isinstance(replies, list) and replies:
                first = replies[0]
                if isinstance(first, dict):
                    ai_reply = first.get("text") or "已分析"
                elif isinstance(first, str):
                    ai_reply = first
                else:
                    ai_reply = str(first)
            elif isinstance(replies, str) and replies.strip():
                ai_reply = replies
            context_user_text = f"[图片分析] {safe_text}" if image_base64 else f"对方说：{safe_text}"
            context.append({"user": context_user_text, "assistant": f"建议回复：{ai_reply}"})
            save_context(context, context_length, session_name, unlimited)
        return result
    except Exception as e:
        try:
            print("CLICK-ANALYZE-EXCEPT-FULL:")
            traceback.print_exc()
        except Exception:
            pass
        err_msg = repr(e) + "\n" + traceback.format_exc()
        if "localhost" in str(getattr(client, 'base_url', '')) or "127.0.0.1" in str(getattr(client, 'base_url', '')):
            err_msg = "请检查本地模型服务是否已启动。" + " 原始错误: " + repr(e)
        return {"surface_answer": "分析失败", "surface_probs": {"错误": 100}, "deep_intents": {"无法连接": 100}, "affinity_score": 50, "danger_level": 0, "best_action": err_msg, "action_advice": "无", "replies": [{"style": "稳妥型", "text": "稍后再试。"}]}


# =========================================================
# 【待办功能 1++ 系统】
# 以下为文档《项目交接与开发文档》中待办模块的完整实现：
#   1) 多世界书（Multi-Lorebook）
#   2) AI 自动写书
#   3) 联网查梗（DuckDuckGo）
#   4) 情景模拟（新手引导）
#   5) 流式输出（stream）
# 全部以独立函数实现,不侵入已有核心逻辑。
# =========================================================

import base64 as _b64
import urllib.parse as _urlparse
import urllib.request as _urlreq

# ---------- 多世界书 & AI自动写书 ----------

def lorebook_prompt_for(book_name="默认", max_terms=20):
    """把某个知识包拼成可注入 system prompt 的文本。"""
    data = load_lorebook(book_name)
    if not data or not data.get("terms"):
        return ""
    desc = f"【世界书背景】{data.get('description', '')}\n" if data.get("description") else ""
    terms = data.get("terms", {})
    lines = [f"- {k}: {v}" for k, v in list(terms.items())[:max_terms]]
    return desc + "【世界书词条】\n" + "\n".join(lines) + "\n"

def ask_model(system, user, temperature=0.8):
    """统一的模型调用封装,返回模型回复文本。"""
    client, model_name = get_client()
    response = None
    for _attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            break
        except Exception as _exc:
            if _attempt == 1:
                raise
            import time as _t
            _t.sleep(1)
    return response.choices[0].message.content

def stable_json_loads(text):
    """稳定的 JSON 解析：清洗围栏+提取大括号块,失败返回 None。"""
    cleaned = clean_json(text)
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # 再试：定位第一个 { 到最后一个 }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(cleaned[start:end + 1])
        except Exception:
            return None
    return None

def auto_sols(chat_text, book_name="默认"):
    """AI 自动写书：从聊天记录提取设定生成知识包并落盘。"""
    data = auto_write_lorebook(book_name, [chat_text] if chat_text else [])
    if data and data.get("terms"):
        return {"ok": True, "data": data}
    return {"ok": False, "data": load_lorebook(book_name)}

# ---------- 联网查梗 ----------

def search_ddg(query, max_results=3):
    """使用 DuckDuckGo 的公共 HTML 接口查梗（无需 API key）。"""
    results = []
    try:
        from bs4 import BeautifulSoup
        url = "https://html.duckduckgo.com/html/?q=" + _urlparse.quote(query)
        req = _urlreq.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _urlreq.urlopen(req, timeout=10) as r:
            html = r.read(100000).decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select(".result__a")[:max_results]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            results.append(title + " " + href)
    except Exception as e:
        results.append(f"查梗失败: {str(e)}")
    try:
        from _debug_logger import log
        log('web_search 返回 %d 条: %r' % (len(results), [r.get("title","")[:30] for r in results[:3]]))
    except Exception:
        pass
    return results if results else ["未找到相关结果"]

# ---------- 情景模拟（新手引导）----------

SCENARIOS = {
    "初次使用": [
        "用户是第一次用Cf助手,需要耐心解释每一步操作。",
        "建议给出一步一步的入门指引。",
    ],
    "一个重要考试": [
        "用户即将参加重要考试,心情紧张,需要鼓励与备考建议。",
        "回答要兼顾情绪安抚和实际方法。",
    ],
    "求职面试": [
        "用户在准备面试,需要打磨自我介绍和模拟问答。",
        "回答要专业,具体,可操作。",
    ],
}

def scenario_prompt(name="初次使用"):
    """根据情景名拼接引导提示文本。"""
    tips = SCENARIOS.get(name)
    if not tips:
        return ""
    return "【情景模拟引导】当前激活情景：" + name + "。\n" + "\n".join(tips) + "\n"

def known_scenarios():
    return list(SCENARIOS.keys())

# ---------- 流式输出 ----------

def stream_reply(prompt_text, system="你是Cf助手", on_chunk=None):
    """以流式方式调用模型,逐段回调 on_chunk(文本块)。返回完整文本。"""
    client, model_name = get_client()
    stream = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt_text},
        ],
        stream=True,
        temperature=0.85,
    )
    full = []
    for chunk in stream:
        piece = ""
        if chunk and getattr(chunk, "choices", None):
            delta = chunk.choices[0].delta
            piece = getattr(delta, "content", "") or ""
        if piece:
            full.append(piece)
            if on_chunk:
                on_chunk(piece)
    return "".join(full)


# =========================================================
# 第三阶段（一）：联网搜索 & AI 自动写书
# 依赖：duckduckgo_search（免费）；Bing / 百度为兜底,无需 API key
# =========================================================

def web_search(query, max_results=3):
    """联网搜索,返回结果列表。每条含 title/body/href。

    搜索顺序：DuckDuckGo（首选,duckduckgo_search 库）→ Bing（兜底）→ 百度（最兜底）。
    任何引擎失败都不会抛异常,保证主流程不断。
    """
    results = []
    try:
        from _debug_logger import log
        log('web_search 入参: query=%r, max_results=%d' % (query, max_results))
    except Exception:
        pass
    # --- 1) DuckDuckGo（首选）---
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, region='cn-zh', safesearch='moderate', max_results=max_results))
        for item in raw:
            title = _html.unescape(str(item.get("title", "") or "")).strip()
            body = _html.unescape(str(item.get("body", "") or "")).strip()
            href = str(item.get("href", "") or "").strip()
            if href:
                results.append({"title": title, "body": body, "href": href})
        if results:
            return results
    except Exception:
        pass

    # --- 2) Bing 兜底（解析 HTML） ---
    try:
        search_url = "https://www.bing.com/search?q=" + _urlparse.quote(query)
        req = _urlreq.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with _urlreq.urlopen(req, timeout=10) as r:
            html_doc = r.read().decode("utf-8", errors="ignore")
        for m in _re.finditer(r'<li class="b_algo".*?</li>', html_doc, _re.S):
            block = m.group(0)
            # 标题：h2 可能带 class，链接可能带额外属性
            title_m = _re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, _re.S)
            # 摘要：Bing 的 <p> 现在几乎都带 class（如 b_lineclamp2），不能只匹配裸 <p>
            body_m = _re.search(r'<p[^>]*>(.*?)</p>', block, _re.S)
            if title_m:
                title = _re.sub(r"<[^>]+>", "", title_m.group(2))
                title = _html.unescape(title).strip()
                href = _html.unescape(title_m.group(1)).strip()
                body = ""
                if body_m:
                    body = _re.sub(r"<[^>]+>", "", body_m.group(1))
                    body = _html.unescape(body).strip()
                results.append({"title": title, "body": body, "href": href})
            if len(results) >= max_results:
                break
        if results:
            return results
    except Exception:
        pass

    # --- 3) 百度 最兜底（解析 HTML） ---
    try:
        search_url = "https://www.baidu.com/s?wd=" + _urlparse.quote(query) + "&rn=10"
        req = _urlreq.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with _urlreq.urlopen(req, timeout=10) as r:
            html_doc = r.read().decode("utf-8", errors="ignore")
        count = 0
        for mm in _re.finditer(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_doc):
            href = _html.unescape(mm.group(1)).strip()
            title = _re.sub(r"<[^>]+>", "", mm.group(2))
            title = _html.unescape(title).strip()
            seg = html_doc[mm.end():mm.end() + 600]
            body = ""
            body_m = _re.search(r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>', seg, _re.S)
            if body_m:
                body = _re.sub(r"<[^>]+>", "", body_m.group(1))
                body = _html.unescape(body).strip()
            if href:
                results.append({"title": title, "body": body, "href": href})
                count += 1
            if count >= max_results:
                break
        if results:
            return results
    except Exception:
        pass

    return results

def _join_search_text(results, max_chars=6000):
    """把搜索结果拼成一段供 LLM 阅读的语料文本。"""
    parts = []
    total = 0
    for i, r in enumerate(results, 1):
        title = str(r.get("title", "") or "").strip()
        body = str(r.get("body", "") or "").strip()
        href = str(r.get("href", "") or "").strip()
        seg = f"[{i}] {title}\n{body}\n来源: {href}".strip()
        if not seg or not title:
            continue
        if total + len(seg) > max_chars:
            continue
        parts.append(seg)
        total += len(seg)
    return "\n\n".join(parts)

def auto_write_lorebook_from_topic(topic, book_name=None, max_results=5):
    """✨ AI自动写书（多路搜索+溯源）：主题/黑话术语/梗语录三路搜索,合并去重,可信源优先,逐条进行溯源。"""
    topic = (topic or "").strip()
    if not topic:
        return {"error": "主题不能为空"}

    all_results = []
    seen = set()
    for q in (topic, topic + " 黑话 术语", topic + " 梗 语录"):
        try:
            for r in web_search(q, max_results=max_results):
                href = r.get("href") or ""
                if href and href not in seen:
                    seen.add(href)
                    r["_src_query"] = q
                    all_results.append(r)
        except Exception:
            continue

    if all_results:
        GOOD = ("baike.baidu.com", "zh.wikipedia.org", "zhihu.com",
                "bilibili.com", "tieba.baidu.com", "moegirl.org")
        def _score(r):
            h = (r.get("href") or "").lower()
            return -sum(1 for g in GOOD if g in h)
        all_results.sort(key=_score)

    context = _join_search_text(all_results) if all_results else (
        "（网络搜索未返回有效结果,请基于自身知识尽可能准确地编写。）"
    )

    client, model_name = get_client()
    prompt = (
        "你是资料整理大师。以下是关于“" + topic +
        "”的多路网络搜索摘要,请据此生成一本高质量世界书（知识包）：\n\n"
        + context + "\n\n"
        "要求：\n"
        "1. 只能采用上述摘要中出现的内容,决不允许自行发挥或编造。\n"
        "2. 每条术语、黑话、梗都必须列出它出现在哪条摘要（用[1][2]...标号标注）。\n"
        "3. 如果某个“黑话”在摘要中绝对找不到依据,就不要写进去。宁可少不可假。\n"
        "4. 输出严格按 JSON,不要语言围栏。结构："
        '{"name": "书名","description": "一句话概括,要提到重要黑话",'
        '"terms": {"黑话1": {"meaning": "解释","source": "[1]"}},'
        '"memes": [{"meme": "梗名","meaning": "来历与用法","source": "[2]"}],'
        '"blacklist": "雷区/禁忌"}\n'
    )
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return {"error": "✨ AI 调用失败: %s" % e}

    data = stable_json_loads(text)
    if not isinstance(data, dict):
        return {"error": "AI 输出不是合法 JSON,请重试"}

    data.setdefault("name", book_name or topic)
    data.setdefault("description", "")
    data.setdefault("blacklist", "")
    data.setdefault("terms", {})
    data.setdefault("memes", [])

    for k, v in list(data.get("terms", {}).items()):
        if isinstance(v, str):
            data["terms"][k] = {"meaning": v, "source": "（未能溯源,请核实）"}

    for m in data.get("memes", []):
        if isinstance(m, dict):
            m.setdefault("source", "（未能溯源,请核实）")

    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["_source"] = "✨ AI自动写书（多路搜索+溯源）"
    if save_lorebook(data):
        return data
    return dict(data, error="写入知识库失败（注意溯源真实性）")
