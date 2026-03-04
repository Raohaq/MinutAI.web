# import os
# import re
# import sys
# import json
# import time
# import tempfile
# import subprocess
# from datetime import datetime
# from typing import List, Tuple, Dict, Any, Optional
# from urllib import request, error

# from faster_whisper import WhisperModel


# # ===========================
# # CONFIG (speed-oriented)
# # ===========================
# DEVICE = "cpu"
# WHISPER_SIZE = os.environ.get("MINUTAI_WHISPER", "base")
# WHISPER_COMPUTE = os.environ.get("MINUTAI_WHISPER_COMPUTE", "int8")

# OLLAMA_URL = os.environ.get("MINUTAI_OLLAMA_URL", "http://localhost:11434/api/generate")
# OLLAMA_MODEL = os.environ.get("MINUTAI_OLLAMA_MODEL", "qwen2.5:7b-instruct")

# # One-shot threshold: if transcript is short, do ONE Ollama call only (fast)
# ONE_SHOT_MAX_CHARS = int(os.environ.get("MINUTAI_ONE_SHOT_MAX_CHARS", "8000"))

# # Chunking for long meetings (bigger chunks = fewer calls = faster)
# CHUNK_MAX_CHARS = int(os.environ.get("MINUTAI_CHUNK_MAX_CHARS", "5000"))
# REDUCE_MAX_CHARS = int(os.environ.get("MINUTAI_REDUCE_MAX_CHARS", "14000"))

# # Output controls
# MAX_ACTION_ITEMS = int(os.environ.get("MINUTAI_MAX_ACTION_ITEMS", "12"))
# MAX_TASK_LEN = int(os.environ.get("MINUTAI_MAX_TASK_LEN", "160"))

# # Ollama generation tokens (lower = faster)
# MAP_MAX_TOKENS = int(os.environ.get("MINUTAI_MAP_MAX_TOKENS", "260"))
# REDUCE_MAX_TOKENS = int(os.environ.get("MINUTAI_REDUCE_MAX_TOKENS", "420"))
# ONE_SHOT_MAX_TOKENS = int(os.environ.get("MINUTAI_ONE_SHOT_MAX_TOKENS", "520"))

# # Ollama runtime options (threads/context)
# # Ryzen 5 5500U is 6C/12T; 8 threads is a safe default
# OLLAMA_THREADS = int(os.environ.get("MINUTAI_OLLAMA_THREADS", "8"))
# OLLAMA_CTX = int(os.environ.get("MINUTAI_OLLAMA_CTX", "4096"))  # helps for longer prompts
# OLLAMA_TEMP = float(os.environ.get("MINUTAI_OLLAMA_TEMP", "0.2"))

# # Small sleep between calls (helps keep UI responsive; keep tiny)
# CALL_PAUSE_SEC = float(os.environ.get("MINUTAI_CALL_PAUSE_SEC", "0.02"))


# # ===========================
# # LOAD MODELS ONCE
# # ===========================
# WHISPER_MODEL = WhisperModel(WHISPER_SIZE, device=DEVICE, compute_type=WHISPER_COMPUTE)


# # ===========================
# # AUDIO HELPERS
# # ===========================
# def ensure_dir(path: str):
#     os.makedirs(path, exist_ok=True)


# def to_wav_16k_mono(input_audio: str) -> str:
#     """Convert audio to 16kHz mono wav (temp file) for stable ASR."""
#     wav_path = os.path.join(
#         tempfile.gettempdir(),
#         f"minutai_{int(datetime.utcnow().timestamp())}_{os.getpid()}.wav"
#     )
#     subprocess.run(
#         ["ffmpeg", "-y", "-i", input_audio, "-ac", "1", "-ar", "16000", wav_path],
#         check=True,
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL,
#     )
#     return wav_path


# def format_ts(seconds: float) -> str:
#     m = int(seconds // 60)
#     s = int(seconds % 60)
#     return f"{m:02d}:{s:02d}"


# # ===========================
# # TEXT HELPERS
# # ===========================
# def clean_text(text: str) -> str:
#     return re.sub(r"\s+", " ", text).strip()


# def remove_problem_content_for_outputs(text: str) -> str:
#     """
#     Replace self-harm phrases in summary/actions input with a neutral marker.
#     Transcript remains raw for transparency.
#     """
#     patterns = [
#         r"\bkill myself\b",
#         r"\bcommit suicide\b",
#         r"\bsuicide\b",
#         r"\bself[- ]harm\b",
#         r"\bi want to die\b",
#         r"\bi'?m going to kill myself\b",
#         r"\bi will jump from the bridge\b",
#         r"\bjump from the bridge\b",
#     ]
#     out = text
#     for p in patterns:
#         out = re.sub(p, "(self-harm statement)", out, flags=re.IGNORECASE)
#     out = re.sub(r"\s+", " ", out).strip()
#     return out


# def split_into_chunks(text: str, max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
#     """Chunk by sentences to keep context coherent; bigger chunks = fewer LLM calls."""
#     text = text.strip()
#     if len(text) <= max_chars:
#         return [text]

#     sentences = re.split(r"(?<=[.!?])\s+", text)
#     chunks, buf = [], ""
#     for s in sentences:
#         if not s:
#             continue
#         if len(buf) + len(s) + 1 <= max_chars:
#             buf = (buf + " " + s).strip()
#         else:
#             if buf:
#                 chunks.append(buf)
#             buf = s
#     if buf:
#         chunks.append(buf)
#     return chunks


# def normalize_task_line(line: str) -> str:
#     line = line.strip()
#     line = re.sub(r"^[-•\d\.\)\s]+", "", line).strip()
#     line = re.sub(r"\s+", " ", line).strip()
#     line = re.sub(r"[;:\-–—\s]+$", "", line).strip()
#     return line


# def looks_like_nontask(task: str) -> bool:
#     low = task.lower().strip()
#     if len(low) < 6:
#         return True
#     if low.endswith("?") and not low.startswith(("please ", "can you ", "could you ")):
#         return True
#     if any(x in low for x in ["how are you", "good night", "hello", "hi ", "(self-harm statement)"]):
#         return True
#     if any(x in low for x in ["what will you do", "then what will you do", "shut your whole computer"]):
#         return True
#     return False


# def dedupe_tasks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     seen = set()
#     out: List[Dict[str, Any]] = []
#     for it in items:
#         task = (it.get("task") or "").strip()
#         key = re.sub(r"[^a-z0-9 ]+", "", task.lower()).strip()
#         key = re.sub(r"\s+", " ", key)
#         if not key or key in seen:
#             continue
#         seen.add(key)
#         out.append(it)
#     return out


# def dedupe_sentences(text: str) -> str:
#     """Remove repeated sentences in summary (common LLM issue)."""
#     text = text.strip()
#     if not text:
#         return ""
#     sents = re.split(r"(?<=[.!?])\s+", text)
#     seen = set()
#     uniq = []
#     for s in sents:
#         k = s.strip().lower()
#         if not k:
#             continue
#         if k in seen:
#             continue
#         seen.add(k)
#         uniq.append(s.strip())
#     return " ".join(uniq).strip()


# # ===========================
# # TRANSCRIPTION
# # ===========================
# def transcribe_with_faster_whisper_timestamped(audio_path: str) -> Tuple[str, str]:
#     segments, _info = WHISPER_MODEL.transcribe(
#         audio_path,
#         language="en",
#         beam_size=1,
#         vad_filter=True,
#         vad_parameters=dict(min_silence_duration_ms=500),
#     )

#     lines, plain_parts = [], []
#     for seg in segments:
#         start = float(seg.start)
#         txt = (seg.text or "").strip()
#         if not txt:
#             continue
#         lines.append(f"[{format_ts(start)}] {txt}")
#         plain_parts.append(txt)

#     timestamped = "\n".join(lines).strip()
#     plain = clean_text(" ".join(plain_parts))
#     return timestamped, plain


# # ===========================
# # OLLAMA CLIENT
# # ===========================
# def ollama_generate(prompt: str, max_tokens: int, temperature: float = OLLAMA_TEMP) -> str:
#     """
#     Calls Ollama /api/generate (non-stream) and returns response text.
#     Thread/context options help speed/stability.
#     """
#     payload = {
#         "model": OLLAMA_MODEL,
#         "prompt": prompt,
#         "stream": False,
#         "options": {
#             "temperature": temperature,
#             "num_predict": max_tokens,
#             "num_thread": OLLAMA_THREADS,
#             "num_ctx": OLLAMA_CTX,
#         }
#     }
#     data = json.dumps(payload).encode("utf-8")
#     req = request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
#     try:
#         with request.urlopen(req, timeout=240) as resp:
#             body = resp.read().decode("utf-8", errors="replace")
#             obj = json.loads(body)
#             return (obj.get("response") or "").strip()
#     except error.URLError as e:
#         raise RuntimeError(f"Ollama call failed: {e}") from e
#     except Exception as e:
#         raise RuntimeError(f"Ollama call failed: {e}") from e


# def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
#     """Extract a JSON object even if model adds extra text."""
#     text = text.strip()
#     try:
#         return json.loads(text)
#     except Exception:
#         pass

#     start = text.find("{")
#     end = text.rfind("}")
#     if start != -1 and end != -1 and end > start:
#         candidate = text[start:end + 1]
#         try:
#             return json.loads(candidate)
#         except Exception:
#             return None
#     return None


# # ===========================
# # ONE-SHOT (fast path)
# # ===========================
# def one_shot_summary_actions(transcript: str) -> Dict[str, Any]:
#     """
#     One Ollama call for short transcripts.
#     Returns {summary, action_items}.
#     """
#     prompt = f"""
# You are an assistant that produces meeting outputs.

# Return ONLY valid JSON:
# {{
#   "summary": "ONE paragraph, 3 to 5 sentences",
#   "action_items": [
#     {{"task": "...", "owner": null, "due": null}}
#   ]
# }}

# Rules:
# - Summary must be a single paragraph, 3–5 sentences, clear and to the point.
# - Include the main topics and any deadlines/decisions mentioned.
# - Do NOT repeat sentences.
# - Action items must be REAL tasks (follow-ups, assignments, submissions).
# - Keep each task short (max 14 words).
# - Remove duplicates.
# - If a due date is mentioned, write it EXACTLY as spoken (do NOT invent a year).
# - If uncertain, due = null.
# - Max 12 action items.
# - No extra keys, no extra text.

# Transcript:
# \"\"\"{transcript}\"\"\"
# """
#     raw = ollama_generate(prompt, max_tokens=ONE_SHOT_MAX_TOKENS, temperature=0.2)
#     obj = extract_json_object(raw)
#     if not isinstance(obj, dict):
#         return {"summary": "", "action_items": []}
#     return obj


# # ===========================
# # MAP-REDUCE (for long meetings)
# # ===========================
# def map_chunk_to_json(chunk_text: str) -> Dict[str, Any]:
#     prompt = f"""
# You extract meeting summaries and action items.

# Return ONLY valid JSON:
# {{
#   "chunk_summary": "short paragraph (2-4 sentences max)",
#   "action_items": [
#     {{"task": "...", "owner": null, "due": null}}
#   ]
# }}

# Rules:
# - chunk_summary: summarize what happened in this chunk.
# - action_items: ONLY real tasks to do, not opinions or long speeches.
# - Keep each task short (max 14 words).
# - If a due date is mentioned, write it EXACTLY as spoken (do NOT invent a year).
# - If uncertain, due = null.
# - owner only if explicitly stated.
# - If no action items, return an empty list.
# - No extra keys, no extra text.

# Transcript chunk:
# \"\"\"{chunk_text}\"\"\"
# """
#     raw = ollama_generate(prompt, max_tokens=MAP_MAX_TOKENS, temperature=0.2)
#     obj = extract_json_object(raw)
#     if not isinstance(obj, dict):
#         return {"chunk_summary": "", "action_items": []}
#     cs = obj.get("chunk_summary") if isinstance(obj.get("chunk_summary"), str) else ""
#     ai = obj.get("action_items") if isinstance(obj.get("action_items"), list) else []
#     return {"chunk_summary": cs.strip(), "action_items": ai}


# def reduce_to_final_json(chunk_summaries: List[str], all_action_items: List[Dict[str, Any]]) -> Dict[str, Any]:
#     combined_summaries = "\n".join(f"- {s}" for s in chunk_summaries if s.strip())
#     if len(combined_summaries) > REDUCE_MAX_CHARS:
#         combined_summaries = combined_summaries[:REDUCE_MAX_CHARS]

#     tasks_text = "\n".join(f"- {it.get('task','')}" for it in all_action_items if isinstance(it, dict))
#     if len(tasks_text) > REDUCE_MAX_CHARS:
#         tasks_text = tasks_text[:REDUCE_MAX_CHARS]

#     prompt = f"""
# You are creating the final meeting summary and action items.

# Return ONLY valid JSON:
# {{
#   "summary": "ONE paragraph, 3 to 5 sentences. No bullet points.",
#   "action_items": [
#     {{"task": "...", "owner": null, "due": null}}
#   ]
# }}

# Summary rules:
# - One paragraph, 3–5 sentences.
# - Clear and to the point; cover main topics and any decisions/deadlines.
# - Do NOT repeat sentences.

# Action rules:
# - Only real tasks (follow-ups/assignments/submissions).
# - Remove duplicates.
# - Keep each task <= 14 words.
# - If a due date is mentioned, write it EXACTLY as spoken (do NOT invent a year).
# - If uncertain, due = null.
# - Max 12.

# Chunk summaries:
# {combined_summaries}

# Candidate action items:
# {tasks_text}
# """
#     raw = ollama_generate(prompt, max_tokens=REDUCE_MAX_TOKENS, temperature=0.2)
#     obj = extract_json_object(raw)
#     if not isinstance(obj, dict):
#         return {"summary": "", "action_items": []}
#     summary = obj.get("summary") if isinstance(obj.get("summary"), str) else ""
#     action_items = obj.get("action_items") if isinstance(obj.get("action_items"), list) else []
#     return {"summary": summary.strip(), "action_items": action_items}


# # ===========================
# # CLEAN ACTION ITEMS
# # ===========================
# def clean_action_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     cleaned: List[Dict[str, Any]] = []
#     for it in items:
#         if not isinstance(it, dict):
#             continue

#         task = normalize_task_line(str(it.get("task", "")))
#         if not task:
#             continue
#         if looks_like_nontask(task):
#             continue
#         if len(task) > MAX_TASK_LEN:
#             continue

#         owner = it.get("owner", None)
#         due = it.get("due", None)

#         if isinstance(owner, str) and owner.strip().lower() in ("", "null", "none"):
#             owner = None
#         if isinstance(due, str):
#             due = due.strip()
#             if due.lower() in ("", "null", "none"):
#                 due = None

#         cleaned.append({"task": task, "owner": owner, "due": due})

#     cleaned = dedupe_tasks(cleaned)
#     return cleaned[:MAX_ACTION_ITEMS]


# # ===========================
# # MAIN ORCHESTRATION
# # ===========================
# def summarize_and_extract_actions(clean_transcript: str) -> Tuple[str, List[Dict[str, Any]]]:
#     safe = remove_problem_content_for_outputs(clean_transcript)
#     if not safe:
#         return "", []

#     # Fast path: one shot
#     if len(safe) <= ONE_SHOT_MAX_CHARS:
#         obj = one_shot_summary_actions(safe)
#         summary = obj.get("summary", "") if isinstance(obj.get("summary"), str) else ""
#         actions = obj.get("action_items", []) if isinstance(obj.get("action_items"), list) else []
#         summary = dedupe_sentences(summary)
#         return summary.strip(), clean_action_items(actions)

#     # Long path: map-reduce
#     chunks = split_into_chunks(safe, CHUNK_MAX_CHARS)

#     chunk_summaries: List[str] = []
#     action_items_all: List[Dict[str, Any]] = []

#     for idx, ch in enumerate(chunks):
#         if idx > 0 and CALL_PAUSE_SEC > 0:
#             time.sleep(CALL_PAUSE_SEC)

#         mapped = map_chunk_to_json(ch)

#         cs = mapped.get("chunk_summary", "")
#         if isinstance(cs, str) and cs.strip():
#             chunk_summaries.append(cs.strip())

#         ai = mapped.get("action_items", [])
#         if isinstance(ai, list):
#             for x in ai:
#                 if isinstance(x, dict):
#                     action_items_all.append(x)

#     final_obj = reduce_to_final_json(chunk_summaries, action_items_all)
#     summary = final_obj.get("summary", "") if isinstance(final_obj.get("summary"), str) else ""
#     actions = final_obj.get("action_items", []) if isinstance(final_obj.get("action_items"), list) else []

#     summary = dedupe_sentences(summary)
#     return summary.strip(), clean_action_items(actions)


# # ===========================
# # FALLBACK (if Ollama fails)
# # ===========================
# def fallback_actions(clean_transcript: str) -> List[Dict[str, Any]]:
#     safe = remove_problem_content_for_outputs(clean_transcript)
#     patterns = [
#         r"\byou have to ([^.?!]{3,120})",
#         r"\bplease ([^.?!]{3,120})",
#         r"\bcan you ([^.?!]{3,120})",
#         r"\bi will ([^.?!]{3,120})",
#         r"\bwe will ([^.?!]{3,120})",
#     ]
#     out = []
#     for p in patterns:
#         for m in re.findall(p, safe, flags=re.IGNORECASE):
#             task = normalize_task_line(m)
#             if not task:
#                 continue
#             if looks_like_nontask(task):
#                 continue
#             if len(task) > MAX_TASK_LEN:
#                 continue
#             out.append({"task": task, "owner": None, "due": None})
#     out = dedupe_tasks(out)
#     return out[:MAX_ACTION_ITEMS]


# # ===========================
# # ENTRYPOINT
# # ===========================
# def main():
#     if len(sys.argv) < 2:
#         raise ValueError("Usage: python pipeline.py <audio_path>")

#     audio_path = sys.argv[1]

#     BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
#     output_dir = os.path.join(BASE_DIR, "outputs")
#     ensure_dir(output_dir)

#     transcript_path = os.path.join(output_dir, "transcript.txt")
#     clean_path = os.path.join(output_dir, "clean_transcript.txt")
#     summary_path = os.path.join(output_dir, "summary.txt")
#     actions_txt_path = os.path.join(output_dir, "action_items.txt")
#     actions_json_path = os.path.join(output_dir, "action_items.json")

#     wav_path = None
#     try:
#         wav_path = to_wav_16k_mono(audio_path)

#         # 1) Transcript
#         timestamped, clean = transcribe_with_faster_whisper_timestamped(wav_path)
#         with open(transcript_path, "w", encoding="utf-8") as f:
#             f.write(timestamped)

#         with open(clean_path, "w", encoding="utf-8") as f:
#             f.write(clean)

#         # 2) Summary + action items via Ollama
#         try:
#             summary, actions = summarize_and_extract_actions(clean)
#         except Exception:
#             summary = ""
#             actions = fallback_actions(clean)

#         with open(summary_path, "w", encoding="utf-8") as f:
#             f.write(summary.strip())

#         with open(actions_json_path, "w", encoding="utf-8") as f:
#             json.dump({"action_items": actions}, f, indent=2, ensure_ascii=False)

#         with open(actions_txt_path, "w", encoding="utf-8") as f:
#             f.write("Action Items:\n")
#             if not actions:
#                 f.write("- None\n")
#             else:
#                 for a in actions:
#                     task = a.get("task", "")
#                     owner = a.get("owner", None)
#                     due = a.get("due", None)
#                     suffix_parts = []
#                     if owner and str(owner).lower() not in ("null", "none", ""):
#                         suffix_parts.append(f"Owner: {owner}")
#                     if due and str(due).lower() not in ("null", "none", ""):
#                         suffix_parts.append(f"Due: {due}")
#                     suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
#                     f.write(f"- {task}{suffix}\n")

#         print("Pipeline completed successfully.")

#     finally:
#         if wav_path and os.path.exists(wav_path):
#             try:
#                 os.remove(wav_path)
#             except Exception:
#                 pass


# if __name__ == "__main__":
#     main()









import os
import re
import sys
import json
import time
import tempfile
import subprocess
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from urllib import request, error

from faster_whisper import WhisperModel


# ===========================
# CONFIG (speed + stability)
# ===========================
DEVICE = "cpu"
WHISPER_SIZE = os.environ.get("MINUTAI_WHISPER", "base")
WHISPER_COMPUTE = os.environ.get("MINUTAI_WHISPER_COMPUTE", "int8")

OLLAMA_URL = os.environ.get("MINUTAI_OLLAMA_URL", "http://localhost:11434/api/generate")
# Default to faster model; can override with env var.
OLLAMA_MODEL = os.environ.get("MINUTAI_OLLAMA_MODEL", "qwen2.5:3b-instruct")

# If transcript is short, do ONE Ollama call only
ONE_SHOT_MAX_CHARS = int(os.environ.get("MINUTAI_ONE_SHOT_MAX_CHARS", "9000"))

# Chunking for long meetings (bigger chunks -> fewer calls)
CHUNK_MAX_CHARS = int(os.environ.get("MINUTAI_CHUNK_MAX_CHARS", "5500"))
REDUCE_MAX_CHARS = int(os.environ.get("MINUTAI_REDUCE_MAX_CHARS", "14000"))

MAX_ACTION_ITEMS = int(os.environ.get("MINUTAI_MAX_ACTION_ITEMS", "12"))
MAX_TASK_LEN = int(os.environ.get("MINUTAI_MAX_TASK_LEN", "160"))

# Lower tokens -> faster
MAP_MAX_TOKENS = int(os.environ.get("MINUTAI_MAP_MAX_TOKENS", "180"))
REDUCE_MAX_TOKENS = int(os.environ.get("MINUTAI_REDUCE_MAX_TOKENS", "260"))
ONE_SHOT_MAX_TOKENS = int(os.environ.get("MINUTAI_ONE_SHOT_MAX_TOKENS", "280"))

# Ollama runtime options
OLLAMA_THREADS = int(os.environ.get("MINUTAI_OLLAMA_THREADS", "8"))
OLLAMA_CTX = int(os.environ.get("MINUTAI_OLLAMA_CTX", "2048"))
OLLAMA_TEMP = float(os.environ.get("MINUTAI_OLLAMA_TEMP", "0.2"))

CALL_PAUSE_SEC = float(os.environ.get("MINUTAI_CALL_PAUSE_SEC", "0.01"))


# ===========================
# LOAD MODELS ONCE
# ===========================
WHISPER_MODEL = WhisperModel(WHISPER_SIZE, device=DEVICE, compute_type=WHISPER_COMPUTE)


# ===========================
# AUDIO HELPERS
# ===========================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def to_wav_16k_mono(input_audio: str) -> str:
    """Convert audio to 16kHz mono wav (temp file)."""
    wav_path = os.path.join(
        tempfile.gettempdir(),
        f"minutai_{int(datetime.utcnow().timestamp())}_{os.getpid()}.wav"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_audio, "-ac", "1", "-ar", "16000", wav_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return wav_path


def format_ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


# ===========================
# TEXT HELPERS
# ===========================
def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def remove_problem_content_for_outputs(text: str) -> str:
    patterns = [
        r"\bkill myself\b",
        r"\bcommit suicide\b",
        r"\bsuicide\b",
        r"\bself[- ]harm\b",
        r"\bi want to die\b",
        r"\bi'?m going to kill myself\b",
        r"\bi will jump from the bridge\b",
        r"\bjump from the bridge\b",
    ]
    out = text
    for p in patterns:
        out = re.sub(p, "(self-harm statement)", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def split_into_chunks(text: str, max_chars: int) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, buf = [], ""
    for s in sentences:
        if not s:
            continue
        if len(buf) + len(s) + 1 <= max_chars:
            buf = (buf + " " + s).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    return chunks


def normalize_task_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[-•\d\.\)\s]+", "", line).strip()
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"[;:\-–—\s]+$", "", line).strip()
    return line


def looks_like_nontask(task: str) -> bool:
    low = task.lower().strip()
    if len(low) < 6:
        return True
    if low.endswith("?") and not low.startswith(("please ", "can you ", "could you ")):
        return True
    if any(x in low for x in ["how are you", "good night", "hello", "hi ", "(self-harm statement)"]):
        return True
    if any(x in low for x in ["what will you do", "then what will you do", "shut your whole computer"]):
        return True
    return False


def dedupe_tasks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        task = (it.get("task") or "").strip()
        key = re.sub(r"[^a-z0-9 ]+", "", task.lower()).strip()
        key = re.sub(r"\s+", " ", key)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def dedupe_sentences(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    sents = re.split(r"(?<=[.!?])\s+", text)
    seen = set()
    uniq = []
    for s in sents:
        k = s.strip().lower()
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s.strip())
    return " ".join(uniq).strip()


# ===========================
# DUE DATE HANDLING (prevents fake ISO 2023-01-06)
# ===========================
def extract_due_phrase(transcript: str) -> Optional[str]:
    # "from January 5th to January 6th"
    m = re.search(
        r"\bfrom\s+((jan(?:uary)?)\s+\d{1,2}(st|nd|rd|th)?)\s+to\s+((jan(?:uary)?)\s+\d{1,2}(st|nd|rd|th)?)\b",
        transcript,
        flags=re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)} to {m.group(4)}"

    # "deadline was from the 5th of January to the 6th"
    m2 = re.search(
        r"\bfrom\s+the\s+(\d{1,2}(st|nd|rd|th)?)\s+of\s+(jan(?:uary)?)\s+to\s+the\s+(\d{1,2}(st|nd|rd|th)?)\b",
        transcript,
        flags=re.IGNORECASE,
    )
    if m2:
        return f"{m2.group(1)} of {m2.group(3)} to {m2.group(4)}"

    return None


def is_iso_date(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s.strip()))


def is_generic_invented_task(task: str) -> bool:
    low = task.lower()
    bad_phrases = [
        "seek additional", "additional resources", "resources or support",
        "review progress", "monitor progress", "track progress",
        "if needed", "as needed", "consider", "ensure", "make sure to", "be sure to",
    ]
    return any(p in low for p in bad_phrases)


# ===========================
# TRANSCRIPTION
# ===========================
def transcribe_with_faster_whisper_timestamped(audio_path: str) -> Tuple[str, str]:
    segments, _info = WHISPER_MODEL.transcribe(
        audio_path,
        language="en",
        beam_size=1,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    lines, plain_parts = [], []
    for seg in segments:
        start = float(seg.start)
        txt = (seg.text or "").strip()
        if not txt:
            continue
        lines.append(f"[{format_ts(start)}] {txt}")
        plain_parts.append(txt)

    timestamped = "\n".join(lines).strip()
    plain = clean_text(" ".join(plain_parts))
    return timestamped, plain


# ===========================
# OLLAMA CLIENT + WARMUP
# ===========================
def ollama_generate(prompt: str, max_tokens: int, temperature: float = OLLAMA_TEMP) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_thread": OLLAMA_THREADS,
            "num_ctx": OLLAMA_CTX,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=240) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            obj = json.loads(body)
            return (obj.get("response") or "").strip()
    except error.URLError as e:
        raise RuntimeError(f"Ollama call failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}") from e


def ollama_warmup():
    # Keeps first real call faster; safe to ignore failures.
    try:
        _ = ollama_generate("Reply with OK.", max_tokens=3, temperature=0.0)
    except Exception:
        pass


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None


# ===========================
# ONE-SHOT (fast path)
# ===========================
def one_shot_summary_actions(transcript: str) -> Dict[str, Any]:
    prompt = f"""
Return ONLY valid JSON:
{{
  "summary": "ONE paragraph, 3 to 5 sentences",
  "action_items": [
    {{"task": "...", "owner": null, "due": null}}
  ]
}}

Rules:
- Summary: one paragraph, 3–5 sentences, clear and to the point, include main topics + any deadlines/decisions.
- No repeated sentences.
- Action items: only real tasks, short (max 14 words), remove duplicates.
- Due dates:
  - Copy EXACTLY as spoken (e.g., "Jan 5 to Jan 6", "January 6th").
  - NEVER output YYYY-MM-DD.
  - Do NOT invent a year.
  - If unsure, due = null.
- Max 12 action items.
- No extra text, no extra keys.

Transcript:
\"\"\"{transcript}\"\"\"
"""
    raw = ollama_generate(prompt, max_tokens=ONE_SHOT_MAX_TOKENS, temperature=0.2)
    obj = extract_json_object(raw)
    if not isinstance(obj, dict):
        return {"summary": "", "action_items": []}
    return obj


# ===========================
# MAP-REDUCE (long meetings)
# ===========================
def map_chunk_to_json(chunk_text: str) -> Dict[str, Any]:
    prompt = f"""
Return ONLY valid JSON:
{{
  "chunk_summary": "2-4 sentences max",
  "action_items": [
    {{"task": "...", "owner": null, "due": null}}
  ]
}}

Rules:
- chunk_summary: summarize this chunk.
- action_items: only real tasks, short (max 14 words).
- Due dates: copy EXACTLY as spoken; NEVER YYYY-MM-DD; do not invent a year.
- If unsure, due = null.
- No extra text, no extra keys.

Chunk:
\"\"\"{chunk_text}\"\"\"
"""
    raw = ollama_generate(prompt, max_tokens=MAP_MAX_TOKENS, temperature=0.2)
    obj = extract_json_object(raw)
    if not isinstance(obj, dict):
        return {"chunk_summary": "", "action_items": []}
    cs = obj.get("chunk_summary") if isinstance(obj.get("chunk_summary"), str) else ""
    ai = obj.get("action_items") if isinstance(obj.get("action_items"), list) else []
    return {"chunk_summary": cs.strip(), "action_items": ai}


def reduce_to_final_json(chunk_summaries: List[str], all_action_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined_summaries = "\n".join(f"- {s}" for s in chunk_summaries if s.strip())
    if len(combined_summaries) > REDUCE_MAX_CHARS:
        combined_summaries = combined_summaries[:REDUCE_MAX_CHARS]

    tasks_text = "\n".join(f"- {it.get('task','')}" for it in all_action_items if isinstance(it, dict))
    if len(tasks_text) > REDUCE_MAX_CHARS:
        tasks_text = tasks_text[:REDUCE_MAX_CHARS]

    prompt = f"""
Return ONLY valid JSON:
{{
  "summary": "ONE paragraph, 3 to 5 sentences",
  "action_items": [
    {{"task": "...", "owner": null, "due": null}}
  ]
}}

Rules:
- Summary: one paragraph, 3–5 sentences, no repetition.
- Action items: only real tasks, short (max 14 words), deduplicate, max 12.
- Due dates: copy EXACTLY as spoken; NEVER YYYY-MM-DD; do not invent a year.
- If unsure, due = null.
- No extra keys.

Chunk summaries:
{combined_summaries}

Candidate tasks:
{tasks_text}
"""
    raw = ollama_generate(prompt, max_tokens=REDUCE_MAX_TOKENS, temperature=0.2)
    obj = extract_json_object(raw)
    if not isinstance(obj, dict):
        return {"summary": "", "action_items": []}

    summary = obj.get("summary") if isinstance(obj.get("summary"), str) else ""
    action_items = obj.get("action_items") if isinstance(obj.get("action_items"), list) else []
    return {"summary": summary.strip(), "action_items": action_items}


# ===========================
# CLEAN ACTION ITEMS (remove hallucinations + ISO dates)
# ===========================
def clean_action_items(items: List[Dict[str, Any]], transcript: str) -> List[Dict[str, Any]]:
    due_phrase = extract_due_phrase(transcript)

    cleaned: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue

        task = normalize_task_line(str(it.get("task", "")))
        if not task:
            continue
        if looks_like_nontask(task):
            continue
        if len(task) > MAX_TASK_LEN:
            continue
        if is_generic_invented_task(task):
            continue

        owner = it.get("owner", None)
        due = it.get("due", None)

        if isinstance(owner, str) and owner.strip().lower() in ("", "null", "none"):
            owner = None

        if isinstance(due, str):
            due = due.strip()
            if due.lower() in ("", "null", "none"):
                due = None
            elif is_iso_date(due):
                due = None
            elif due.lower() not in transcript.lower():
                # enforce "copy as spoken"
                due = None
        else:
            due = None

        cleaned.append({"task": task, "owner": owner, "due": due})

    cleaned = dedupe_tasks(cleaned)

    # If meeting clearly contains a due range and tasks have no due, attach it
    if due_phrase:
        any_due = any(x.get("due") for x in cleaned)
        if not any_due:
            for x in cleaned:
                x["due"] = due_phrase

    return cleaned[:MAX_ACTION_ITEMS]


# ===========================
# ORCHESTRATION
# ===========================
def summarize_and_extract_actions(clean_transcript: str) -> Tuple[str, List[Dict[str, Any]]]:
    safe = remove_problem_content_for_outputs(clean_transcript)
    if not safe:
        return "", []

    ollama_warmup()

    # One-shot (fast) for short transcripts
    if len(safe) <= ONE_SHOT_MAX_CHARS:
        obj = one_shot_summary_actions(safe)
        summary = obj.get("summary", "") if isinstance(obj.get("summary"), str) else ""
        actions = obj.get("action_items", []) if isinstance(obj.get("action_items"), list) else []
        summary = dedupe_sentences(summary)
        return summary.strip(), clean_action_items(actions, safe)

    # Chunked for long transcripts
    chunks = split_into_chunks(safe, CHUNK_MAX_CHARS)

    chunk_summaries: List[str] = []
    action_items_all: List[Dict[str, Any]] = []

    for idx, ch in enumerate(chunks):
        if idx > 0 and CALL_PAUSE_SEC > 0:
            time.sleep(CALL_PAUSE_SEC)

        mapped = map_chunk_to_json(ch)

        cs = mapped.get("chunk_summary", "")
        if isinstance(cs, str) and cs.strip():
            chunk_summaries.append(cs.strip())

        ai = mapped.get("action_items", [])
        if isinstance(ai, list):
            for x in ai:
                if isinstance(x, dict):
                    action_items_all.append(x)

    final_obj = reduce_to_final_json(chunk_summaries, action_items_all)
    summary = final_obj.get("summary", "") if isinstance(final_obj.get("summary"), str) else ""
    actions = final_obj.get("action_items", []) if isinstance(final_obj.get("action_items"), list) else []

    summary = dedupe_sentences(summary)
    return summary.strip(), clean_action_items(actions, safe)


# ===========================
# FALLBACK (if Ollama fails)
# ===========================
def fallback_actions(clean_transcript: str) -> List[Dict[str, Any]]:
    safe = remove_problem_content_for_outputs(clean_transcript)
    patterns = [
        r"\byou have to ([^.?!]{3,120})",
        r"\bplease ([^.?!]{3,120})",
        r"\bcan you ([^.?!]{3,120})",
        r"\bi will ([^.?!]{3,120})",
        r"\bwe will ([^.?!]{3,120})",
    ]
    out = []
    for p in patterns:
        for m in re.findall(p, safe, flags=re.IGNORECASE):
            task = normalize_task_line(m)
            if not task:
                continue
            if looks_like_nontask(task):
                continue
            if len(task) > MAX_TASK_LEN:
                continue
            if is_generic_invented_task(task):
                continue
            out.append({"task": task, "owner": None, "due": None})
    out = dedupe_tasks(out)
    return out[:MAX_ACTION_ITEMS]


# ===========================
# MAIN
# ===========================
def main():
    if len(sys.argv) < 2:
        raise ValueError("Usage: python pipeline.py <audio_path>")

    audio_path = sys.argv[1]

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
    output_dir = os.path.join(BASE_DIR, "outputs")
    ensure_dir(output_dir)

    transcript_path = os.path.join(output_dir, "transcript.txt")
    clean_path = os.path.join(output_dir, "clean_transcript.txt")
    summary_path = os.path.join(output_dir, "summary.txt")
    actions_txt_path = os.path.join(output_dir, "action_items.txt")
    actions_json_path = os.path.join(output_dir, "action_items.json")

    wav_path = None
    try:
        wav_path = to_wav_16k_mono(audio_path)

        # 1) Transcript
        timestamped, clean = transcribe_with_faster_whisper_timestamped(wav_path)
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(timestamped)

        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(clean)

        # 2) Summary + action items
        try:
            summary, actions = summarize_and_extract_actions(clean)
        except Exception:
            summary = ""
            actions = fallback_actions(clean)

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary.strip())

        with open(actions_json_path, "w", encoding="utf-8") as f:
            json.dump({"action_items": actions}, f, indent=2, ensure_ascii=False)

        with open(actions_txt_path, "w", encoding="utf-8") as f:
            f.write("Action Items:\n")
            if not actions:
                f.write("- None\n")
            else:
                for a in actions:
                    task = a.get("task", "")
                    owner = a.get("owner", None)
                    due = a.get("due", None)
                    suffix_parts = []
                    if owner and str(owner).lower() not in ("null", "none", ""):
                        suffix_parts.append(f"Owner: {owner}")
                    if due and str(due).lower() not in ("null", "none", ""):
                        suffix_parts.append(f"Due: {due}")
                    suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
                    f.write(f"- {task}{suffix}\n")

        print("Pipeline completed successfully.")

    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()