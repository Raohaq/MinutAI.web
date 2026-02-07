from transformers import T5Tokenizer, T5ForConditionalGeneration
import os

# Project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

input_path = os.path.join(BASE_DIR, "outputs", "clean_transcript.txt")
output_path = os.path.join(BASE_DIR, "outputs", "summary.txt")

# Load model
# print("Loading T5 model...")
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")

# Read input
with open(input_path, "r", encoding="utf-8") as f:
    text = f.read()

# Prepare input for T5
input_text = "summarize: " + text

inputs = tokenizer.encode(
    input_text,
    return_tensors="pt",
    max_length=512,
    truncation=True
)

# Generate summary
# summary_ids = model.generate(
#     inputs,
#     max_length=150,
#     min_length=40,
#     length_penalty=2.0,
#     num_beams=4,
#     early_stopping=True
# )
summary_ids = model.generate(
    inputs,
    max_length=180,
    min_length=60,
    num_beams=6,
    repetition_penalty=2.5,
    length_penalty=1.5,
    early_stopping=True
)


summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# Save output
with open(output_path, "w", encoding="utf-8") as f:
    f.write(summary)

# print("\n Summary generated successfully:")
# print(summary)
