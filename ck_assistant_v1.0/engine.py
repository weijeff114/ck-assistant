import json
from openai import OpenAI

# 读取配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def get_client():
    provider = config["provider"]
    cfg = config[provider]
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"]), cfg["model"]

def clean_json(text):
    """清理模型可能输出的多余字符"""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def analyze_chat(chat_text):
    client, model_name = get_client()
    
    # 泛化后的提示词，主角叫 Cf
    system_prompt = """
    你是名为"Cf"的高情商聊天辅助AI。你的任务是分析用户提供的对方发来的消息（朋友、同事、群友、暧昧对象等均适用）。
    你必须严格输出纯JSON格式，不要包含任何多余的文字。
    JSON结构必须包含以下字段：
    {
        "intent_analysis": {"闲聊": 30, "寻求建议": 70}, 
        "affinity_score": 75, 
        "danger_level": 3, 
        "best_action": "倾听共情", 
        "suggested_reply": "确实，这周末好好放松一下最重要。", 
        "alternative_reply": "哈哈，那你这周末打算去哪玩？" 
    }
    字段解释：
    - intent_analysis: 分析对方的真实意图，概率总和必须等于100
    - affinity_score: 对方当前对用户的好感度/情绪值（0-100分，50为中性，低于30为冷淡/生气，高于80为热情/开心）
    - danger_level: 当前聊天危险等级（1-10分，1为绝对安全，10为踩雷/极度危险）
    - best_action: 建议动作（如"倾听共情", "幽默化解", "给出行动方案", "谨慎转移话题"等）
    - suggested_reply: 建议回复话术（中文，接地气）
    - alternative_reply: 备选回复话术（中文，另一种风格）
    """
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"对方说：{chat_text}"}
            ],
            temperature=0.4, 
        )
        
        raw_content = response.choices[0].message.content
        clean_content = clean_json(raw_content)
        return json.loads(clean_content)
        
    except Exception as e:
        print(f"调用模型失败: {e}")
        return {
            "intent_analysis": {"分析失败": 100},
            "affinity_score": 50,
            "danger_level": 0,
            "best_action": "检查Ollama是否启动或API Key是否正确",
            "suggested_reply": "系统开小差了，稍后再试。",
            "alternative_reply": "我要睡觉了。"
        }