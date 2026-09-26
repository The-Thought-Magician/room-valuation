"""Local model wrappers. One model on the GPU at a time: 8 GB does not hold all three."""

import contextlib

import torch
from PIL import Image

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OWL_ID = "google/owlv2-base-patch16-ensemble"
VLM_ID = "Qwen/Qwen3-VL-2B-Instruct"
ASR_ID = "openai/whisper-large-v3-turbo"

torch.backends.cuda.enable_cudnn_sdp(False)  # cuDNN SDPA is unreliable on Blackwell


GPU_LOCK_FILE = "/tmp/room_valuation_gpu.lock"


@contextlib.contextmanager
def gpu_lock():
    """One GPU job at a time across every process (server jobs and command-line replays).
    Two jobs sharing the 8 GB card crashed one with a CUDA illegal memory access (2026-09-26)."""
    import fcntl

    with open(GPU_LOCK_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield  # the lock goes with the file when it closes


def free():
    if DEVICE == "cuda":
        torch.cuda.empty_cache()


class Detector:
    """OWLv2 open-vocabulary detection. Boxes come back normalized to [0, 1]."""

    def __init__(self):
        from transformers import Owlv2ForObjectDetection, Owlv2Processor

        self.processor = Owlv2Processor.from_pretrained(OWL_ID)
        self.model = Owlv2ForObjectDetection.from_pretrained(OWL_ID).to(DEVICE).eval()

    def detect(self, image: Image.Image, prompts: list[str], threshold: float) -> list[dict]:
        inputs = self.processor(text=[prompts], images=image, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            outputs = self.model(**inputs)
        side = max(image.size)  # OWLv2 pads to a square
        det = self.processor.post_process_grounded_object_detection(
            outputs, threshold=threshold, target_sizes=torch.tensor([[side, side]], device=DEVICE), text_labels=[prompts]
        )[0]
        w, h = image.size
        rows = zip(det["scores"].tolist(), det["labels"].tolist(), det["boxes"].tolist(), strict=True)
        return [
            {"prompt": prompts[label], "score": round(float(score), 3),
             "box": [max(0, x0 / w), max(0, y0 / h), min(1, x1 / w), min(1, y1 / h)]}
            for score, label, (x0, y0, x1, y1) in rows
        ]


class VLM:
    """Qwen3-VL-2B for crop identification, spine reading and text extraction."""

    def __init__(self):
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        dtype = torch.bfloat16 if DEVICE == "cuda" else torch.float32
        model = Qwen3VLForConditionalGeneration.from_pretrained(VLM_ID, dtype=dtype, attn_implementation="sdpa")
        self.model = model.to(DEVICE).eval()
        self.processor = AutoProcessor.from_pretrained(VLM_ID)

    def ask(self, prompt: str, image: Image.Image | None = None, max_new_tokens: int = 256) -> str:
        content = ([{"type": "image", "image": image}] if image is not None else []) + [{"type": "text", "text": prompt}]
        inputs = self.processor.apply_chat_template(
            [{"role": "user", "content": content}], add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt",
        ).to(DEVICE)
        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        return self.processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()


def load_audio(path: str, rate: int = 16000):
    """Any phone format (webm/opus from Chrome, m4a from iPhone) to 16 kHz mono float32 via ffmpeg."""
    import subprocess

    import numpy as np

    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(rate), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def transcribe(audio_paths: list[str]) -> dict[str, list[dict]]:
    """Whisper large-v3-turbo, loaded once for all clips. Returns {path: [{start, end, text}]}."""
    from transformers import pipeline

    asr = pipeline("automatic-speech-recognition", model=ASR_ID, dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                   device=DEVICE, model_kwargs={"attn_implementation": "sdpa"})
    out = {}
    for p in audio_paths:
        audio = load_audio(p)
        if audio.size < 1600:  # under 0.1 s: nothing was said
            out[p] = []
            continue
        res = asr({"raw": audio, "sampling_rate": 16000}, chunk_length_s=30, batch_size=4, return_timestamps=True,
                  generate_kwargs={"language": "en", "task": "transcribe"})
        out[p] = [{"start": c["timestamp"][0], "end": c["timestamp"][1], "text": c["text"].strip()} for c in res["chunks"]]
    del asr
    free()
    return out
