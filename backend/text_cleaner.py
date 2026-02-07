import re
import os
import time

# Get project root dynamically
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

input_path = os.path.join(BASE_DIR, "outputs", "transcript.txt")
output_path = os.path.join(BASE_DIR, "outputs", "clean_transcript.txt")

# with open(input_path, "r", encoding="utf-8") as f:
#     text = f.read()
# Retry reading transcript (avoids Windows/OneDrive file lock)
for _ in range(10):
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
        break
    except PermissionError:
        time.sleep(0.3)
else:
    raise PermissionError(f"Could not access {input_path}. File may be locked.")


# Remove filler words
fillers = ["uh", "um", "you know", "like", "complete"]
for filler in fillers:
    text = re.sub(rf"\b{re.escape(filler)}\b", "", text, flags=re.IGNORECASE)

# Remove extra spaces
text = re.sub(r"\s+", " ", text).strip()

with open(output_path, "w", encoding="utf-8") as f:
    f.write(text)

# print("Clean transcript saved successfully.")
