with open("/root/.gemini/antigravity-ide/brain/b6f589f2-a754-46d6-96b1-daf02541d734/.system_generated/tasks/task-638.log", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

lines = text.splitlines()
start = False
for l in lines:
    if "06:48:20" in l:
        start = True
    if start:
        print(l)
