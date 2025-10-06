const WS_URL = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.hostname + ':8000/v1/asr/stream';
const TTS_URL = location.protocol + '//' + location.hostname + ':8000/v1/tts/synthesize';

let ws, mediaRecorder, chunks = [], stream;
const transcriptDiv = document.getElementById('transcript');
const player = document.getElementById('player');

function appendText(t){ transcriptDiv.textContent = (transcriptDiv.textContent + ' ' + t).trim() }

document.getElementById('startBtn').onclick = async () => {
  stream = await navigator.mediaDevices.getUserMedia({audio: true});
  ws = new WebSocket(WS_URL);
  ws.binaryType = 'arraybuffer';
  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.partial) appendText(msg.partial);
      if (msg.final) appendText('\n' + msg.final + '\n');
      if (msg.reply_url) { player.src = msg.reply_url; player.play(); }
    } catch(e){ console.log('WS message', evt.data) }
  };
  ws.onopen = () => {
    mediaRecorder = new MediaRecorder(stream, {mimeType: 'audio/webm'});
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) e.data.arrayBuffer().then(buf => ws.send(buf)) };
    mediaRecorder.start(250);
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
  };
};

document.getElementById('stopBtn').onclick = () => {
  if(mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  if(ws && ws.readyState === WebSocket.OPEN) ws.close();
  if(stream) stream.getTracks().forEach(t => t.stop());
  document.getElementById('startBtn').disabled = false;
  document.getElementById('stopBtn').disabled = true;
};
