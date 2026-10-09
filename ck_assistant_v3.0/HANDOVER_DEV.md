# 📋 交接文档：ck_assistant_v3.0 多世界书系统

## 一、项目位置与运行环境
- 项目根目录：D:\Projects\ck_assistant_v3.0
- 操作系统：Windows
- 执行命令必须用 Windows PowerShell（禁止 WSL/bash）
- 语法检查：python -m py_compile [文件].py
- 禁止运行 main.py（会弹 GUI 卡死）

## 二、单句话任务
把 ui_lorebook.py 里空壳的「多世界书（知识包）管理系统」补成真正可用：能增、删、改世界书，并让用户在主界面勾选启用，「按需组装进 System Prompt」。

## 三、已完成的进度（关键时刻）
1. Git 存档成功：提交 1408601 / 1234abc ，message「多世界书功能开发前的存档」，20 文件、7291 行。
2. 已读交接文档：HANDOVER.md（拆分指南）与 WORK.txt（多世界书改造需求，含逐行改动点）。
3. 代码已拆分：main.py(入口)、ui.py(主窗口)、ui_settings.py、ui_lorebook.py(16行空壳)、engine.py(核心)、engine_config.py(配置底层)。
4. 已重写 ui_lorebook.py：现约 8KB，语法通过 py_compile。包含 LoremanerDialog 类 + loremaner_prompt_for() 函数。
5. 已确认现状：
   - config.json 位于用户主目录 ~/.config/ckassistant/（不是项目目录）
   - 目前 config.json 没有 lorebooks / session_lorebooks 字段
   - engine.list_lorebooks() 硬编码返回 ['默认']，不是从配置/目录读的

## 四、关键代码定位
- engine.py：
  - get_lorebook_dir() 返回知识包存储目录
  - get_lorebook_path(book) 
  - list_lorebooks()：硬编码 ['默认']（要改成真实读配置）
  - load_lorebook(book) 读取单本
  - save_lorebook(data) 写
  - delete_lorebook(book) 删
  - analyze_chat(...) 约453行 sel_books = config.get("selected_lorebooks", [])（要改为 session 级）
  - lorebook_prompt_for(book, max_terms=20) 拼知识包为 prompt 文本
- ui_lorebook.py（刚重写）：
  - LoremanerDialog(QDialog) 类
  - loremaner_prompt_for(book, max_terms) 独立函数
- ui.py：
  - 旧 LoremanerManagerDialog（约781行）——按 HANDLE 要求应删除，由新 LoremanerDialog 替代
  - 工具栏有 lorebook_combo（单选下拉）——应改为多选 CheckBox 组
  - get_extra_options() 返回选中配置

## 五、改造清单（按 HANDLE 规划）
1. 数据结构（config.json 嵌套）：
   {
     "lorebooks": {
       "书名": {"description":"核心机制","blacklist":"雷区","terms":{"黑话":"解释"},"last_used":"时间戳"}
     },
     "session_lorebooks": { "会话名": ["启用的书名", ...] }
   }
2. Engine：新增 get_session_lorebooks(会话名)/set_session_lorebooks(会话名, 列表)，改造 analyze_chat 第453行为 session 级，只把勾选的注入 System Prompt。
3. UI：主界面加「多选 CheckBox 组 + 管理按钮」；管理弹窗用 LoremanerDialog；删除旧 LoremanerManagerDialog。

## 六、遗留测试文件（重要）
- 项目中已有 _test_lorebook.py（已创建但从未成功运行）：
  内容：强制写一本测试书 -> 读回 -> 调 lorebook_prompt_for 验证。
- 接手第一步应运行它：
  cd D:\Projects\ck_assistant_v3.0
  python _test_lorebook.py
- 若报错（如 lorebook_prompt_for 引用旧结构），以报错为线索改代码。

## 七、给下一位的建议
1. 先跑 _test_lorebook.py，用真实报错定位，而不是重新读代码。
2. list_lorebooks() 的硬编码 ['默认'] 是第一个要修的 bug：应该从配置文件的 lorebooks 字段读真实书名。
3. 改动后自测：python -c "import engine; print(engine.list_lorebooks())" 确保不报错再交付。

—— 交接完，下一位从这里继续

## 八、第三阶段（联网与进化）需求追加

### 4. AI 自动写书与联网查梗
- 输入一个主题（如“明日方舟”），AI 自动去网上搜索游戏机制、社区黑话、热门梗，自动整理成一本独立的“知识包”（写入 config.json 的 lorebooks 字段）。
- 提供「查梗」按钮：遇到不懂的新词，一键搜索并沉淀入当前知识包中。

### 5. 情景模拟（新手引导）
- 用户首次启动时，可选进行几个极简的情景模拟（比如朋友邀约、领导突袭）。
- AI 通过用户的真实回答，自动提取用户的专属说话风格（如“喜欢用短句”“不用感叹号”），自动写入配置（建议字段 personal_style 或新增 style_profile）。
- engine.py 已有 SCENARIOS / scenario_prompt / known_scenarios 雏形，需接入 UI 与自动提取逻辑。
