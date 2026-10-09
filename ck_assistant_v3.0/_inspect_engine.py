import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
p = Path(r"D:\Projects\ck_assistant_v3.0\engine.py")
raw = p.read_bytes()
text = p.read_text(encoding='utf-8')
lines = text.split('\r\n') if '\r\n' in text else text.split('\n')
# 显示 178-248 行的 repr（关键信息：哪些行是def，是否为CRLF）
output = []
for i in range(177, 248):
    l = lines[i]
    output.append(f'{i+1}|{repr(l)[:80]}')
with open(r"D:\Projects\ck_assistant_v3.0\_inspect_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
print("done, wrote", len(output), "lines")
