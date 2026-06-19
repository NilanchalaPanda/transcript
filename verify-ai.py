# verify_ai.py

import torch

print("Torch:", torch.__version__)

try:
    import whisperx
    print("WhisperX OK")
except Exception as e:
    print("WhisperX ERROR:", e)

try:
    import pyannote.audio
    print("Pyannote OK")
except Exception as e:
    print("Pyannote ERROR:", e)

try:
    from faster_whisper import WhisperModel
    print("Faster Whisper OK")
except Exception as e:
    print("Faster Whisper ERROR:", e)