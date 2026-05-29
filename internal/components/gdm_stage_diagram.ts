import { LitElement, css, html, PropertyValues } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-diagram-view — A2UI panel component.
 * Renders a live architecture diagram from raw SVG markup.
 * Props: diagId, svg, version.
 *
 * Sanitizes incoming SVG via DOMPurify when available (loaded globally on
 * the stage page), then injects it into a shadow-DOM host div.  After
 * injection the inner <svg> element is post-processed: width/height attrs
 * are stripped, preserveAspectRatio is set, and a fade-in transition is
 * applied via a rAF tick.
 */
@customElement('gdm-diagram-view')
export class GdmStageDiagram extends LitElement {
  /** Identifier for this diagram — used as a key and in logging. */
  @property({ type: String }) diagId = '';

  /** Raw SVG markup to render. */
  @property({ type: String }) svg = '';

  /** Bump to signal a forced re-render even when svg content is identical. */
  @property({ type: Number }) version = 0;

  /** Render as a full-stage glassmorphic overlay. */
  @property({ type: Boolean, reflect: true }) overlay = false;

  // Track the last-rendered svg + version so we only re-inject when needed.
  private _renderedSvg = '';
  private _renderedVersion = -1;

  static styles = css`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: rgba(8, 10, 20, 0.82);
      box-sizing: border-box;
    }

    :host([overlay]) {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 999;
      /* Solid full-screen dark — same value the stage uses — so the
         letterboxing from preserveAspectRatio:meet blends into the stage
         instead of reading as a centred dark card on a darker backdrop. */
      background: #000;
      padding: 0;
      box-sizing: border-box;
      animation: backdrop-fade-in 220ms ease-out forwards;
    }

    /* True fullscreen — no centred-card chrome (no max-width / max-height /
       border / radius). The diagram itself owns the whole viewport, with a
       small inset so its edges don't kiss the screen. */
    :host([overlay]) .diagram-host {
      width: 100%;
      height: 100%;
      padding: 16px;
      box-sizing: border-box;
      animation: scale-up 320ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
    }

    @keyframes backdrop-fade-in {
      from { opacity: 0; }
      to   { opacity: 1; }
    }

    @keyframes scale-up {
      from {
        transform: scale(0.92);
        opacity: 0;
      }
      to {
        transform: scale(1);
        opacity: 1;
      }
    }

    .diagram-host {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      padding: 16px;
      box-sizing: border-box;
    }

    /* SVG node is styled imperatively after injection; these rules act as
       safe defaults in case the element is already present. The SVG fills
       its host; preserveAspectRatio="xMidYMid meet" keeps the diagram
       proportional (letterboxed if needed) instead of stretching. */
    .diagram-host svg {
      width: 100%;
      height: 100%;
      display: block;
      border-radius: 12px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
      transition: opacity 400ms ease-out;
    }

    .placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      opacity: 0.28;
      animation: pulse 2.2s ease-in-out infinite alternate;
      pointer-events: none;
      user-select: none;
    }

    .placeholder svg {
      width: 40px;
      height: 40px;
      box-shadow: none;
      border-radius: 0;
    }

    .placeholder-text {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.6);
      letter-spacing: 0.04em;
      text-align: center;
    }

    @keyframes pulse {
      from { opacity: 0.15; }
      to   { opacity: 0.38; }
    }
  `;

  render() {
    if (!this.svg || !this.svg.trim()) {
      return html`
        <div class="diagram-host">
          <div class="placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <path d="M17.5 17.5m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>
              <line x1="6.5" y1="10" x2="6.5" y2="14"/>
              <line x1="17.5" y1="10" x2="17.5" y2="14"/>
              <line x1="6.5" y1="14" x2="17.5" y2="14"/>
            </svg>
            <span class="placeholder-text">Awaiting diagram</span>
          </div>
        </div>
      `;
    }

    // Render the container; actual SVG injection happens in updated().
    return html`<div class="diagram-host"></div>`;
  }

  updated(changedProps: PropertyValues) {
    super.updated(changedProps);

    // Only re-inject when svg or version actually changed.
    if (!changedProps.has('svg') && !changedProps.has('version')) return;
    if (!this.svg || !this.svg.trim()) return;

    // Avoid redundant injections (e.g. version bump with unchanged content
    // can still force re-render as intended by changing _renderedVersion).
    const sameContent =
      this._renderedSvg === this.svg && this._renderedVersion === this.version;
    if (sameContent) return;

    this._renderedSvg = this.svg;
    this._renderedVersion = this.version;

    this._injectSvg();
  }

  private _injectSvg() {
    const host = this.shadowRoot?.querySelector<HTMLDivElement>('.diagram-host');
    if (!host) return;

    // Sanitize — use DOMPurify when globally available on the page, otherwise
    // fall back to the raw string. The SVG profile lets <defs>, <filter>,
    // <pattern>, <feGaussianBlur>, <feMerge> through (needed by the polish
    // layer's glow); ADD_TAGS: ['style'] explicitly keeps <style> blocks so
    // d2's embedded @font-face declarations + our marching-ants @keyframes
    // both survive. Without ADD_TAGS the SVG profile alone has been observed
    // to drop <style> in some DOMPurify versions, which kills custom fonts.
    const domPurify = (window as any).DOMPurify;
    const sanitized: string = domPurify
      ? domPurify.sanitize(this.svg, {
          USE_PROFILES: { svg: true, svgFilters: true },
          ADD_TAGS: ['style'],
        })
      : this.svg;

    if (!sanitized || !sanitized.trim()) {
      console.warn(`[gdm-diagram-view] diagId=${this.diagId}: sanitized SVG is empty — skipping render`);
      return;
    }

    host.innerHTML = sanitized;

    const svgEl = host.querySelector<SVGSVGElement>('svg');
    if (!svgEl) {
      console.warn(`[gdm-diagram-view] diagId=${this.diagId}: no <svg> element found after injection`);
      return;
    }

    // Strip fixed dimensions so the SVG scales responsively. Use 'meet' so
    // the whole diagram is always visible (slice was cropping too aggressively
    // on overlay). The letterboxing previously made it LOOK like a centred
    // card because of the dark-blue card backdrop — the overlay :host
    // background is now solid full-stage-dark so the letterbox just blends
    // into the stage rather than looking framed.
    svgEl.removeAttribute('width');
    svgEl.removeAttribute('height');
    svgEl.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    // Fill the host via inline styles (CSS rules above are a backup). With
    // preserveAspectRatio="xMidYMid meet" set on the <svg> above, the
    // diagram scales up to fill the panel while preserving aspect ratio;
    // without this, a width/height-less SVG falls back to the browser
    // default 300×150 and sits tiny in the middle of the host.
    svgEl.style.width = '100%';
    svgEl.style.height = '100%';
    svgEl.style.display = 'block';
    svgEl.style.borderRadius = '12px';
    svgEl.style.boxShadow = '0 10px 40px rgba(0,0,0,0.5)';
    svgEl.style.transition = 'opacity 400ms ease-out';

    // Fade in.
    svgEl.style.opacity = '0';
    requestAnimationFrame(() => {
      svgEl.style.opacity = '1';
    });

    console.log(`[gdm-diagram-view] diagId=${this.diagId} rendered (version=${this.version})`);
  }
}
