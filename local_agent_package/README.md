# Local Personal Assistant Agent (Ollama-based)
A fully local, offline personal assistant that talks to a locally-deployed LLM via Ollama.
No API keys, no cloud. Includes:
- Node.js backend that proxies to Ollama and provides tools + memory APIs
- Python RAG service (embeddings + retrieval) using sentence-transformers + chromadb
- React (Vite) frontend with chat UI and voice input (MediaRecorder)
- Electron wrapper for a "Jarvis-like" desktop app
- Speech-to-text integration (VOSK / whisper.cpp options) and TTS (pyttsx3)

**Important**: This repo contains templates and working code, but you must install the recommended open-source packages locally:
- Ollama (https://ollama.com) and at least one model (e.g. `ollama pull llama3`)
- Node.js (>=16), npm
- Python 3.9+, pip

See each subfolder for instructions.
