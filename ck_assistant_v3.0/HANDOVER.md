# Cf 助手 v3.0 —— 代码拆分交接指南

生成时间：2026-10-09

## 一、项目现状（拆分完成后）

项目路径：D:\Projects\ck_assistant_v3.0

| 文件 | 行数 | 职责 |
|------|------|------|
| main.py        | 179 | 桌面端入口：线程调度、快捷键、信号连接、全局托盘 |
| ui.py          | 903 | 主窗口 CfWindow、背景容器 BackgroundFrame、对象设定弹窗 ProfileDialog（含世界书管理入口），顶部 import 新文件 |
| ui_settings.py | 333 | 设置弹窗 SettingsDialog（原 ui.py 78~398 行迁移），含配置表单与存储逻辑 |
| ui_lorebook.py |  16 | 世界书管理弹窗 LorebookDialog（新框架空壳，待开发） |
| engine.py      | 652 | 核心逻辑：AI 对话编排、prompt 组装、世界书注入、推理与流式回复 |
| engine_config.py | 105 | 配置读写底层：USER_HOME / CONFIG_DIR / CONFIG_FILE / DEFAULT_CONFIG + load_config / save_config / get_file路径 / 备份 |

## 二、本次拆分做了什么

1. ui.py 拆出 SettingsDialog → ui_settings.py（完整迁移，UI import 已更新）
2. ui.py 拆出基础 LorebookDialog 框架 → ui_lorebook.py（空壳，待开发）
3. engine.py 拆出 4 个配置底层函数 → engine_config.py，engine.py 顶部 re-import，保证旧调用不变
4. 全部文件通过 python -m py_compile

## 三、模块依赖

main.py --> ui.py --> ui_settings.py
                     --> ui_lorebook.py（待接入）
             engine.py --> engine_config.py

## 四、配置存储结构（目标）

config.json:
- lorebooks: { 书名: {description, terms, last_updated} }   # 多世界书嵌套存储
- session_lorebooks: { 会话名: [启用书名...] }               # 会话级勾选持久化

engine_config.load_config() 负责旧字段自动迁移

## 五、遗留 TODO

1. 【重要】ui.py 第 781 行仍有旧类 LorebookManagerDialog（旧单文件式），建议用 ui_lorebook.py 的 LorebookDialog 替换后删除
2. engine 的 list/load/save/delete_lorebook 已适配新存储，但 UI 旧调用点未迁移
3. get/set_selected_lorebooks 已实现，UI checkbox 组未接入

## 六、测试命令

1. python -m py_compile ui.py ui_settings.py ui_lorebook.py engine.py engine_config.py main.py
2. python -c "from engine import create_lorebook,list_lorebooks,set_selected_lorebooks,get_selected_lorebooks; create_lorebook('A','d',{'k':'v'})"
3. python main.py

## 七、注意事项

- 全部 UTF-8 编码、CRLF 换行
- 修改 ui_settings.py / engine.py 时保持顶层 re-import 同步
- 破坏性修改前先备份（现有备份：ui.py.bak_split_start、ui.py.bak_before_engine、engine.py.bak_split_start、engine.py.bak_before_cfg）
