import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-video-panel')
export class GdmStageVideoPanel extends LitElement {
  @property({ type: String }) src = '';
  @property({ type: Boolean }) autoplay = true;
  @property({ type: Number }) panel = 0;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      background: #000;
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

  render() {
    if (!this.src) {
      return html`<div class="placeholder">📺</div>`;
    }

    const videoId = this._extractYouTubeId(this.src);

    if (videoId) {
      const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=${this.autoplay ? 1 : 0}&mute=1&playsinline=1&rel=0&modestbranding=1`;
      return html`
        <iframe
          src="${embedUrl}"
          style="width:100%;height:100%;border:none;"
          allow="autoplay; encrypted-media; fullscreen"
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
