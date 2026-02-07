import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

input_path = os.path.join(BASE_DIR, "outputs", "clean_transcript.txt")
output_path = os.path.join(BASE_DIR, "outputs", "action_items.txt")

with open(input_path, "r", encoding="utf-8") as f:
    text = f.read()

actions = []

# Simple rule-based patterns
task_patterns = [
    r"you have to ([^.]+)",
    r"complete ([^.]+)",
    r"make ([^.]+)"
]

for pattern in task_patterns:
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    for match in matches:
        actions.append(match.strip())

# Deadline extraction
deadlines = re.findall(r"\b\d{1,2}(st|nd|rd|th)? of \w+", text, flags=re.IGNORECASE)

with open(output_path, "w", encoding="utf-8") as f:
    f.write("Action Items:\n")
    for action in set(actions):
        f.write(f"- {action}\n")

    if deadlines:
        f.write("\nDeadlines:\n")
        for d in deadlines:
            f.write(f"- {d}\n")

actions = list(set(actions))

# print("Action items extracted successfully.")
