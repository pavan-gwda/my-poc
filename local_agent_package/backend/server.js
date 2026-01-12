const express = require('express');
const axios = require('axios');
const cors = require('cors');
const fs = require('fs');
const multer = require('multer');
const path = require('path');
const { exec } = require('child_process');
const searchTool = require("./tools/search");
const systemTool = require("./tools/system");
const fileTool = require("./tools/files");

const AGENT_SYSTEM_PROMPT = `
You are a local offline personal assistant with tool use.

TOOLS YOU CAN USE:
- search(query) → call POST /api/tools/search
- system(command) → call POST /api/tools/system
- files(action, path, content) → call POST /api/tools/files
- rag(query) → call POST /rag/query
- memory.read → GET /memory
- memory.write(text) → write into memory.json

RULES:
- Use external internet APIs only for search and use the search tool.
- ALWAYS return responses in JSON:
{
  "thought": "<explain your reasoning>",
  "action": "<tool_name or none>",
  "input": {}
}

If no tool is needed:
{
  "thought": "I can answer directly.",
  "action": "none",
  "reply": "<your answer>"
}
`;


const app = express();
app.use(cors());
app.use(express.json());

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434/api/generate";
const MEMORY_FILE = path.join(__dirname, "memory.json");

if (!fs.existsSync(MEMORY_FILE)) fs.writeFileSync(MEMORY_FILE, JSON.stringify({ conversations: [] }, null, 2));

// Simple chat endpoint that forwards to Ollama
app.post('/chat', async (req, res) => {
  try {
    const { prompt, history } = req.body;

    const finalPrompt =
      AGENT_SYSTEM_PROMPT +
      "\n\nUser message:\n" +
      prompt;

    const payloadPrompt = {
      model: process.env.OLLAMA_MODEL || "llama3:latest",
      prompt: finalPrompt,
      stream: false
    };

    const r = await axios.post(OLLAMA_URL, payloadPrompt);
    const reply = r.data?.response || (r.data && JSON.stringify(r.data)) || "No response";

    // Save memory
    const mem = JSON.parse(fs.readFileSync(MEMORY_FILE));
    mem.conversations.push({ prompt, reply, ts: new Date().toISOString() });
    fs.writeFileSync(MEMORY_FILE, JSON.stringify(mem, null, 2));

    res.json({ reply });
  } catch (err) {
    console.error(err?.response?.data || err.message);
    res.status(500).json({ error: err?.message || "failed" });
  }
});


// Simple memory endpoints
app.get('/memory', (req, res) => {
  const mem = JSON.parse(fs.readFileSync(MEMORY_FILE));
  res.json(mem);
});
app.post('/memory/clear', (req, res) => {
  fs.writeFileSync(MEMORY_FILE, JSON.stringify({ conversations: [] }, null, 2));
  res.json({ ok:true });
});

// Upload audio for STT
const upload = multer({ dest: path.join(__dirname, 'uploads/') });
app.post('/speech/upload', upload.single('audio'), async (req, res) => {
  // This endpoint saves audio for the local STT service to pick up.
  // You can implement VOSK / whisper.cpp processing here locally.
  res.json({ filename: req.file.filename, path: req.file.path });
});

// Proxy to Python RAG service (runs separately)
app.post('/rag/query', async (req, res) => {
  try {
    const r = await axios.post('http://localhost:8001/query', req.body, { timeout: 60000 });
    res.json(r.data);
  } catch (e) {
    res.status(500).json({ error: "RAG service not available. Start python/rag_service.py" , details: e.message });
  }
});

// Tool: run a local command (DANGEROUS — use only locally and secure)
app.post('/tool/run', async (req, res) => {
  const { cmd } = req.body;
  if (!cmd) return res.status(400).json({ error: 'cmd required' });
  // VERY IMPORTANT: this runs shell commands. Use only on trusted machine.
  exec(cmd, { timeout: 30_000 }, (err, stdout, stderr) => {
    if (err) return res.status(500).json({ error: err.message, stderr });
    res.json({ stdout });
  });
});

app.post("/api/tools/search", async (req, res) => {
  const { query } = req.body;
  res.json(await searchTool(query));
});

app.post("/api/tools/system", async (req, res) => {
  const { command } = req.body;
  res.json(await systemTool(command));
});

app.post("/api/tools/files", async (req, res) => {
  const { action, path, content } = req.body;
  res.json(await fileTool(action, path, content));
});


const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Backend listening on http://localhost:${PORT}`));
