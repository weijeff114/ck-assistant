# Cf 助手 / ck-assistant
# Copyright (c) 2026 Wei Qiguang (weijeff114)
# SPDX-License-Identifier: GPL-3.0-only

import sys
import io
import json
import os
import traceback
import time
from datetime import datetime


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
        }
    },
    "background_image": "",
    "chat_mode": "single",
    "context_length": 4,
    "input_height": 120,
    "unlimited_memory": False,
    "enable_mad_style": True,
    "enable_madder_style": True,
    "enable_offend_style": True,
    "sessions": ["默认单聊"],
    "current_session": "默认单聊",
    "session_profiles": {
        "默认单聊": "未知，普通朋友，语气适中"
    },
    "session_backgrounds": {
        "默认单聊": ""
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

def backup_corrupt_file(file_path):
    """文件损坏时，先把损坏的文件备份为 原名.bak_时间戳，避免数据直接丢光。"""
    try:
        if os.path.exists(file_path):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{file_path}.bak_{timestamp}"
            os.rename(file_path, backup_path)
            print(f"⚠️ 检测到损坏的 JSON 文件，已备份为：{backup_path}")
    except Exception as e:
        print(f"⚠️ 备份损坏文件失败: {e}")

