import React, {useState, useRef} from 'react'


export default function App(){
  const [prompt, setPrompt] = useState('');
  const [reply, setReply] = useState('');
  const [history, setHistory] = useState([]);
  const mediaRecorderRef = useRef(null);

  async function ask(){
    const res = await fetch('http://localhost:3000/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ prompt, history })
    });
    const d = await res.json();
    setReply(d.reply);
    setHistory(prev => [...prev, {prompt, reply: d.reply}]);
  }

  // Simple voice recording (browser MediaRecorder) and upload
  async function startRecording(){
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    const chunks = [];
    mediaRecorder.addEventListener('dataavailable', e => chunks.push(e.data));
    mediaRecorder.addEventListener('stop', async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const fd = new FormData();
      fd.append('audio', blob, 'speech.webm');
      const r = await fetch('http://localhost:3000/speech/upload', { method:'POST', body: fd });
      const data = await r.json();
      console.log('uploaded', data);
      alert('Audio uploaded to backend for local STT processing: ' + data.filename);
    });
    mediaRecorder.start();
    setTimeout(()=> mediaRecorder.stop(), 3000); // record 3s for demo
  }

  return (
    <div style={{maxWidth:800, margin:'20px auto', fontFamily:'sans-serif'}}>
      <h1>Pavan Kumar's Jarvis</h1>
      <textarea rows={4} style={{width:'100%'}} value={prompt} onChange={e=>setPrompt(e.target.value)} />
      <div style={{marginTop:10}}>
        <button onClick={ask}>Ask</button>
        <button onClick={startRecording} style={{marginLeft:10}}>Record (3s)</button>
      </div>

      <h3>Reply</h3>
      <pre style={{background:'#f5f5f5', padding:10}}>{reply}</pre>

      <h3>History</h3>
      <ul>
        {history.map((h,i)=> <li key={i}><b>Q:</b> {h.prompt} <br/><b>A:</b> {h.reply}</li>)}
      </ul>
    </div>
  );
}
