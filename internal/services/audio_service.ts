/**
 * AudioService handles the recording (16kHz) and playback (24kHz) contexts.
 */
export class AudioService {
  private recordingContext: AudioContext | null = null;
  private playbackContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private playbackNextTime = 0;

  constructor() {}

  /**
   * Initializes both contexts. Must be called in a user gesture context.
   */
  async initialize() {
    if (this.recordingContext) return;

    this.recordingContext = new AudioContext({ sampleRate: 16000 });
    this.playbackContext = new AudioContext({ sampleRate: 24000 });

    await this.recordingContext.audioWorklet.addModule('/pcm-recorder-processor.js');
    this.workletNode = new AudioWorkletNode(this.recordingContext, 'pcm-recorder-processor');
    
    this.analyser = this.recordingContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.workletNode.connect(this.analyser);
    
    // Playback starting point
    this.playbackNextTime = this.playbackContext.currentTime;
  }

  getAnalyser() { return this.analyser; }
  getWorkletNode() { return this.workletNode; }
  getRecordingContext() { return this.recordingContext; }

  async playChunk(data: ArrayBuffer) {
    if (!this.playbackContext) return;
    const ctx = this.playbackContext;
    
    try {
      const float32 = new Float32Array(data.byteLength / 2);
      const int16 = new Int16Array(data);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0;
      }
      
      const buffer = ctx.createBuffer(1, float32.length, 24000);
      buffer.getChannelData(0).set(float32);
      
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      
      const startTime = Math.max(ctx.currentTime, this.playbackNextTime);
      source.start(startTime);
      this.playbackNextTime = startTime + buffer.duration;
    } catch (e) {
      console.error('[audio] Playback error:', e);
    }
  }

  async resume() {
    if (this.recordingContext?.state === 'suspended') await this.recordingContext.resume();
    if (this.playbackContext?.state === 'suspended') await this.playbackContext.resume();
  }

  disconnect() {
    this.workletNode?.disconnect();
    this.analyser?.disconnect();
    this.recordingContext?.close();
    this.playbackContext?.close();
    this.recordingContext = null;
    this.playbackContext = null;
  }
}
