/**
 * WebSocketService manages the agent connection and PCM buffering.
 */
export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private pcmBuffer: Int16Array[] = [];
  private pcmBufferSamples = 0;
  private static readonly PCM_SEND_SAMPLES = 1600; // 100ms at 16kHz

  constructor(
    private readonly onMessage: (msg: WebSocketMessage | ArrayBuffer) => void,
    private readonly onError: (err: any) => void
  ) {}

  connect(url: string, initData: any) {
    this.ws = new WebSocket(url);
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = () => {
      this.ws?.send(JSON.stringify({
        type: 'init',
        ...initData
      }));
    };

    this.ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) {
        this.onMessage(e.data);
      } else {
        try {
          const msg = JSON.parse(e.data);
          this.onMessage(msg);
        } catch (e) {
          console.error('[ws] Parse error:', e);
        }
      }
    };

    this.ws.onerror = (e) => this.onError(e);
  }

  sendAudio(pcm: Int16Array) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    this.pcmBuffer.push(pcm);
    this.pcmBufferSamples += pcm.length;

    if (this.pcmBufferSamples >= WebSocketService.PCM_SEND_SAMPLES) {
      const merged = new Int16Array(this.pcmBufferSamples);
      let offset = 0;
      for (const b of this.pcmBuffer) {
        merged.set(b, offset);
        offset += b.length;
      }
      this.ws.send(merged.buffer);
      this.pcmBuffer = [];
      this.pcmBufferSamples = 0;
    }
  }

  sendJson(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
    this.pcmBuffer = [];
    this.pcmBufferSamples = 0;
  }

  get readyState() {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}
