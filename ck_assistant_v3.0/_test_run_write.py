# -*- coding: utf-8 -*-
# 测试文件写入机制
from pathlib import Path
p = Path(r"D:\Projects\ck_assistant_v3.0\_test_write.py")
p.write_text("print('hello from test file')\n", encoding='utf-8')
print("file written")
