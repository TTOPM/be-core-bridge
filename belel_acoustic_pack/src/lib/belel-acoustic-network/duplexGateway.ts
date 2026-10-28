import type { DuplexModelAdapter, DuplexModelEvent, PCMFrame } from './types.ts';
/**
 * Belel Gateway Protocol v1 (NOT the native Kyutai/NVIDIA protocol).
 * A self-hosted translation service maps JSON+PCM frames onto Moshi/PersonaPlex codecs.
 * There is no auto-play, automatic TTS selection, or replacement of Belel Core.
 */
export class BelelSelfHostedDuplexGateway implements DuplexModelAdapter {
  readonly supportsDuplex = true as const;
  private ws: WebSocket | null = null;
  private sink: ((event: DuplexModelEvent) => void) | null = null;
  constructor(readonly id: string, private readonly url: string, private readonly authToken?: string) {
    const parsed = new URL(url);
    const local = ['localhost','127.0.0.1','[::1]'].includes(parsed.hostname);
    if (parsed.protocol !== 'wss:' && !(local && parsed.protocol === 'ws:')) throw new Error('TLS required for non-local full-duplex gateways');
    if (!id || id.length > 100) throw new Error('Bad model id');
  }
  async start(onEvent: (event: DuplexModelEvent) => void): Promise<void> {
    if (this.ws) throw new Error('Session already started');
    this.sink = onEvent;
    const socket = new WebSocket(this.url);
    socket.binaryType = 'arraybuffer';
    this.ws = socket;
    try {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Duplex gateway timeout')), 6000);
        socket.addEventListener('open', () => { clearTimeout(timeout); resolve(); }, { once: true });
        socket.addEventListener('error', () => { clearTimeout(timeout); reject(new Error('Duplex gateway error')); }, { once: true });
        socket.addEventListener('close', () => { clearTimeout(timeout); reject(new Error('Duplex gateway closed')); }, { once: true });
      });
      socket.onmessage = ev => {
        try {
          if (typeof ev.data !== 'string') return;
          const message = JSON.parse(ev.data) as { type?:string; text?:string; pcm16le_b64?:string; detail?:string };
          const kinds = ['audio.delta','transcript.delta','turn.started','turn.ended','error','health'];
          if (!message.type || !kinds.includes(message.type)) return;
          // Audio is never rendered without the owner's explicit playback integration.
          const event: DuplexModelEvent = { kind: message.type as DuplexModelEvent['kind'], text: message.text, detail: message.detail };
          if (message.type === 'audio.delta' && message.pcm16le_b64) {
            const decoded = atob(message.pcm16le_b64);
            if (decoded.length > 192_000) throw new Error('Oversized audio delta');
            event.audio = Uint8Array.from(decoded, c => c.charCodeAt(0));
          }
          this.sink?.(event);
        } catch { this.sink?.({ kind:'error', detail:'invalid_duplex_gateway_message' }); }
      };
      socket.send(JSON.stringify({ type:'hello', schema:'belel.duplex.v1', model:this.id, ...(this.authToken ? { token:this.authToken } : {}) }));
    } catch (err) { socket.close(); this.ws=null; throw err; }
  }
  async send(frame: PCMFrame): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error('No active duplex session');
    if (frame.source !== 'existing-capture') throw new Error('Only existing authorised capture can be forwarded');
    if (frame.sampleRate !== 24000) throw new Error('Full-duplex gateway expects 24 kHz mono input');
    if (!frame.pcm.length || frame.pcm.length > 24000) throw new Error('Audio frame must be 1–1000ms');
    // Convert PCM16LE, then send a schema-defined JSON delta, not an undocumented model frame.
    const out = new Uint8Array(frame.pcm.length * 2), view = new DataView(out.buffer);
    for (let i=0; i<frame.pcm.length; i++) view.setInt16(i*2, Math.round(Math.max(-1,Math.min(1,frame.pcm[i]))*32767), true);
    let chars=''; for (let i=0; i<out.length; i+=0x4000) chars+=String.fromCharCode(...out.subarray(i,i+0x4000));
    this.ws.send(JSON.stringify({ type:'audio.frame', sample_rate:24000, pcm16le_b64:btoa(chars), at:frame.at }));
  }
  async stop(): Promise<void> {
    const ws = this.ws; this.ws=null; this.sink=null;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type:'close' }));
    ws?.close();
  }
}
