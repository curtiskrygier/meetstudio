import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-video-panel')
export class GdmStageVideoPanel extends LitElement {
  @property({ type: String }) src = '';
  @property({ type: Boolean }) autoplay = true;
  @property({ type: Number }) panel = 0;
  /** Pop the video as a full-viewport overlay (mirrors gdm-diagram-view). */
  @property({ type: Boolean, reflect: true }) overlay = false;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      background: #000;
    }
    :host([overlay]) {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 999;
      background: #000;
      animation: vp-backdrop-fade 280ms ease-out forwards;
    }
    @keyframes vp-backdrop-fade {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    .placeholder {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 64px;
      opacity: 0.4;
    }
  `;

  private _extractYouTubeId(src: string): string | null {
    if (!src) return null;
    let match: RegExpMatchArray | null;
    match = src.match(/youtu\.be\/([A-Za-z0-9_-]{11})/);
    if (match) return match[1];
    match = src.match(/[?&]v=([A-Za-z0-9_-]{11})/);
    if (match) return match[1];
    match = src.match(/embed\/([A-Za-z0-9_-]{11})/);
    if (match) return match[1];
    if (/^[A-Za-z0-9_-]{11}$/.test(src)) return src;
    return null;
  }

  /** Pull a start-time (seconds) from the src URL if present.
   *  Accepts ?t=10 / &t=10s / ?start=10 — strips a trailing 's'. */
  private _extractStartSeconds(src: string): number | null {
    if (!src) return null;
    const m = src.match(/[?&](?:t|start)=(\d+)s?/);
    if (!m) return null;
    const n = parseInt(m[1], 10);
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  render() {
    if (!this.src) {
      return html`<div class="placeholder">📺</div>`;
    }

    const videoId = this._extractYouTubeId(this.src);

    if (videoId) {
      const start = this._extractStartSeconds(this.src);
      const startParam = start ? `&start=${start}` : '';
      // Use youtube.com (not youtube-nocookie.com): some videos — notably
      // music-label uploads like OK Go — refuse to play on the privacy-
      // enhanced variant even when their watch page reports
      // playableInEmbed:true. The cookied embed honours referrer + uses
      // looser playback rights. CSP allows both hosts (see main.py).
      const embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=${this.autoplay ? 1 : 0}&mute=1&playsinline=1&rel=0&modestbranding=1${startParam}`;
      return html`
        <iframe
          src="${embedUrl}"
          style="width:100%;height:100%;border:none;"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>
      `;
    }

    return html`
      <video
        src="${this.src}"
        ?autoplay=${this.autoplay}
        playsinline
        muted
        style="width:100%;height:100%;object-fit:cover;"
      ></video>
    `;
  }
}
