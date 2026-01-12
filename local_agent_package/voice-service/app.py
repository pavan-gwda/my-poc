from flask import Flask, request, jsonify, send_file
from vosk import Model, KaldiRecognizer
import subprocess, json, os, wave
import pyttsx3
# Optional: Coqui
# from TTS.api import TTS

app = Flask(__name__)

# -----------------------------
# LOAD MODELS
# -----------------------------
print("Loading Vosk STT model...")
MODEL_PATH = "model/vosk/"
vosk_model = Model(MODEL_PATH)

print("Initializing TTS...")
engine = pyttsx3.init()   # for offline TTS

# Optional Coqui:
# tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")


# -----------------------------
# STT — Audio Upload
# -----------------------------
@app.route("/stt", methods=["POST"])
def stt_route():
    if "audio" not in request.files:
        return jsonify({"error": "no audio file"}), 400

    file = request.files["audio"]
    save_path = "temp.webm"
    file.save(save_path)

    # Convert WebM → WAV (PCM 16)
    wav_path = "speech.wav"
    subprocess.run([
        "ffmpeg", "-i", save_path, "-ar", "16000",
        "-ac", "1", "-f", "wav", wav_path, "-y"
    ])

    # Run Vosk
    wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(vosk_model, wf.getframerate())

    text = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            text = json.loads(rec.Result())["text"]

    if not text:
        text = json.loads(rec.FinalResult())["text"]

    return jsonify({"text": text})


# -----------------------------
# TTS — Speak text
# -----------------------------
@app.route("/tts", methods=["POST"])
def tts_route():
    data = request.json
    text = data.get("text", "")

    output_file = "tts_output.wav"

    engine.save_to_file(text, output_file)
    engine.runAndWait()

    return send_file(output_file, mimetype="audio/wav")


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/ping")
def ping():
    return "Speech service OK"


if __name__ == "__main__":
    print("Speech service running on http://localhost:5005")
    app.run(host="0.0.0.0", port=5005)
