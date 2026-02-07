import whisper
import os
import sys
import subprocess, os, tempfile




# print("Loading Whisper model...")
# model = whisper.load_model("base")
model = whisper.load_model("small")

if len(sys.argv) < 2:
    raise ValueError("Audio path not provided. Usage: python whisper_test.py <audio_path>")

audio_path = sys.argv[1]

wav_path = os.path.join(tempfile.gettempdir(), "minutai_input.wav")
subprocess.run([
    "ffmpeg", "-y",
    "-i", audio_path,
    "-ac", "1", "-ar", "16000",
    wav_path
], check=True)

audio_path = wav_path

# outputs folder (shared)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_dir = os.path.join(BASE_DIR, "outputs")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "transcript.txt")

# print("Transcribing audio...")
# result = model.transcribe(audio_path)
# result = model.transcribe(audio_path, language="en", task="transcribe")
result = model.transcribe(
    audio_path,
    language="en",
    task="transcribe",
    temperature=0.0,
    fp16=False,
    verbose=False
)


transcript = result["text"]

with open(output_path, "w", encoding="utf-8") as f:
    f.write(transcript)

# print("Transcript saved to outputs/transcript.txt")
