import { LitElement, css, html } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';

interface Flight {
  callsign: string;
  altitude: number;
  speed: number;
  vrate: number;
  origin?: string;
  destination?: string;
}

interface Waypoint {
  alt: number;
  x: number;
  y: number;
}

interface Point3D {
  x: number; // Ground East-West (positive East)
  y: number; // Ground North-South (positive North)
  z: number; // Vertical Altitude
}

interface Point2D {
  u: number;
  v: number;
  depth: number;
}

const FLIGHT_WAYPOINTS: Record<string, Waypoint[]> = {
  'AFR6129': [
    { alt: 6000, x: -12, y: -15 },
    { alt: 3000, x: -6, y: -8 },
    { alt: 1000, x: -2, y: -2.5 },
    { alt: 0, x: 0, y: 0 }
  ],
  'BAW373': [
    { alt: 6000, x: 12, y: -8 },
    { alt: 3500, x: 6, y: -10 },
    { alt: 2000, x: -4, y: -5 },
    { alt: 0, x: 0, y: 0 }
  ],
  'EZY4218': [
    { alt: 6000, x: 5, y: 15 },
    { alt: 4000, x: 12, y: 5 },
    { alt: 2500, x: 2, y: -6 },
    { alt: 0, x: 0, y: 0 }
  ],
  'RYR109B': [
    { alt: 6000, x: -15, y: 2 },
    { alt: 4000, x: -10, y: -10 },
    { alt: 2000, x: -4, y: -5 },
    { alt: 0, x: 0, y: 0 }
  ],
  'DLH11A': [
    { alt: 6000, x: -10, y: 15 },
    { alt: 4500, x: -16, y: 0 },
    { alt: 3000, x: -8, y: -12 },
    { alt: 1500, x: -3, y: -4 },
    { alt: 0, x: 0, y: 0 }
  ]
};

function getWaypointsForFlight(callsign: string): Waypoint[] {
  if (FLIGHT_WAYPOINTS[callsign]) {
    return FLIGHT_WAYPOINTS[callsign];
  }
  let hash = 0;
  for (let i = 0; i < callsign.length; i++) {
    hash = callsign.charCodeAt(i) + ((hash << 5) - hash);
  }
  const startAngle = (Math.abs(hash) % 360) * Math.PI / 180;
  const radius = 12 + (Math.abs(hash) % 8);
  return [
    { alt: 6000, x: radius * Math.cos(startAngle), y: radius * Math.sin(startAngle) },
    { alt: 4000, x: radius * 0.7 * Math.cos(startAngle + 0.4), y: radius * 0.7 * Math.sin(startAngle + 0.4) },
    { alt: 2000, x: radius * 0.35 * Math.cos(startAngle + 1.0), y: radius * 0.35 * Math.sin(startAngle + 1.0) },
    { alt: 0, x: 0, y: 0 }
  ];
}

function getFlight3DPosition(flight: Flight): { x: number; y: number; z: number; heading: number } {
  const alt = typeof flight.altitude === 'number' ? flight.altitude : 3000;
  const waypoints = getWaypointsForFlight(flight.callsign);
  let w1 = waypoints[0];
  let w2 = waypoints[waypoints.length - 1];

  if (alt >= w1.alt) {
    return { x: w1.x, y: w1.y, z: alt, heading: Math.atan2(w2.y - w1.y, w2.x - w1.x) };
  }
  if (alt <= w2.alt) {
    return { x: w2.x, y: w2.y, z: alt, heading: Math.atan2(w2.y - w1.y, w2.x - w1.x) };
  }

  for (let i = 0; i < waypoints.length - 1; i++) {
    if (alt <= waypoints[i].alt && alt >= waypoints[i+1].alt) {
      w1 = waypoints[i];
      w2 = waypoints[i+1];
      break;
    }
  }

  const denom = w1.alt - w2.alt;
  const t = denom === 0 ? 0 : (alt - w2.alt) / denom;
  const x = w2.x + t * (w1.x - w2.x);
  const y = w2.y + t * (w1.y - w2.y);

  const dx = w2.x - w1.x;
  const dy = w2.y - w1.y;
  const heading = Math.atan2(dy, dx);

  return { x, y, z: alt, heading };
}

@customElement('gdm-3d-airspace')
export class GdmStage3DAirspace extends LitElement {
  @property({ type: Array }) flights: Flight[] = [];
  @property({ type: String }) lockedCallsign = '';
  @property({ type: Number }) cameraPitch = 30; // Pitch angle in degrees (5 to 85)
  @property({ type: Number }) cameraYaw = 45;   // Yaw angle in degrees (0 to 360)
  @property({ type: Boolean }) showGlideSlope = true;
  @property({ type: Boolean }) showTerrain = true;
  @property({ type: Number }) zoom = 10.0;
  @property({ type: Boolean }) cinematicOrbit = false;
  @property({ type: Boolean }) autoTrack = false;

  @state() private _canvasW = 400;
  @state() private _canvasH = 400;
  @state() private _activeTab = '3d'; // side panels: '3d', 'traffic'
  @state() private _showAltDropLines = true;
  @state() private _showTrails = true;
  @state() private _showCylinders = true;

  @query('canvas') private _canvas!: HTMLCanvasElement;

  private _ctx: CanvasRenderingContext2D | null = null;
  private _animationFrameId: number | null = null;
  private _resizeObserver: ResizeObserver | null = null;
  private _trails = new Map<string, Point3D[]>();

  // Drag interaction variables
  private _isDragging = false;
  private _lastPointerX = 0;
  private _lastPointerY = 0;

  // Render loop control
  private _radarSweepAngle = 0;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      background: rgb(5, 8, 22);
      font-family: 'Google Sans', 'Inter', monospace;
    }

    .tma-deck-container {
      display: flex;
      flex-direction: row;
      width: 100%;
      height: 100%;
      box-sizing: border-box;
    }

    .viewport-wrapper {
      flex: 1;
      position: relative;
      height: 100%;
      min-width: 0;
      background: radial-gradient(circle at center, rgb(8, 14, 36) 0%, rgb(4, 7, 18) 100%);
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
      cursor: grab;
      touch-action: none;
    }

    canvas:active {
      cursor: grabbing;
    }

    /* Premium Neon Overlay panels */
    .hud-title-bar {
      position: absolute;
      top: 14px;
      left: 16px;
      pointer-events: none;
      z-index: 10;
    }

    .hud-title {
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #00f2ff;
      text-shadow: 0 0 10px rgba(0, 242, 255, 0.4);
      margin: 0 0 4px 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .hud-title .live-pulse {
      width: 6px;
      height: 6px;
      background: #00ff88;
      border-radius: 50%;
      box-shadow: 0 0 8px #00ff88;
    }

    .hud-subtitle {
      font-size: 9px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.5);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    /* Side HUD panels */
    .hud-side-panel {
      width: 250px;
      height: 100%;
      background: rgba(4, 8, 20, 0.85);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-left: 1px solid rgba(0, 242, 255, 0.15);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      z-index: 20;
    }

    .panel-tabs {
      display: flex;
      border-bottom: 1px solid rgba(0, 242, 255, 0.15);
    }

    .tab-btn {
      flex: 1;
      background: none;
      border: none;
      color: rgba(255, 255, 255, 0.4);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .tab-btn:hover {
      color: rgba(255, 255, 255, 0.8);
      background: rgba(0, 242, 255, 0.03);
    }

    .tab-btn.active {
      color: #00f2ff;
      background: rgba(0, 242, 255, 0.08);
      border-bottom: 2px solid #00f2ff;
    }

    .panel-content {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    /* HUD Roster rows */
    .flight-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      border-radius: 6px;
      background: rgba(0, 242, 255, 0.02);
      border: 1px solid rgba(0, 242, 255, 0.05);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .flight-row:hover {
      background: rgba(0, 242, 255, 0.08);
      border-color: rgba(0, 242, 255, 0.2);
    }

    .flight-row.locked {
      background: rgba(0, 242, 255, 0.12);
      border-color: rgba(0, 242, 255, 0.45);
      box-shadow: 0 0 10px rgba(0, 242, 255, 0.05);
    }

    .flight-row-left {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .flight-row-callsign {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
    }

    .flight-row-route {
      font-size: 8px;
      color: rgba(255, 255, 255, 0.4);
      text-transform: uppercase;
    }

    .flight-row-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .flight-row-fl {
      font-size: 10px;
      font-family: monospace;
      color: rgba(255, 255, 255, 0.8);
      background: rgba(255, 255, 255, 0.05);
      padding: 2px 4px;
      border-radius: 3px;
    }

    .flight-row-vrate {
      font-size: 10px;
      font-weight: bold;
    }

    /* Camera & HUD controls */
    .hud-controls-overlay {
      position: absolute;
      top: 14px;
      right: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 10;
    }

    .controls-group {
      background: rgba(4, 10, 26, 0.8);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(0, 242, 255, 0.2);
      border-radius: 8px;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .controls-label {
      font-size: 8px;
      font-weight: 700;
      color: rgba(0, 242, 255, 0.6);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 2px;
    }

    .preset-row {
      display: flex;
      gap: 4px;
    }

    .control-btn {
      background: rgba(0, 242, 255, 0.06);
      border: 1px solid rgba(0, 242, 255, 0.15);
      color: rgba(0, 242, 255, 0.9);
      font-size: 9px;
      font-weight: bold;
      padding: 5px 8px;
      border-radius: 4px;
      cursor: pointer;
      text-transform: uppercase;
      transition: all 0.15s ease;
    }

    .control-btn:hover {
      background: rgba(0, 242, 255, 0.18);
      border-color: rgba(0, 242, 255, 0.35);
      color: #ffffff;
    }

    .toggle-control {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 4px 6px;
      border-radius: 4px;
      cursor: pointer;
    }

    .toggle-control:hover {
      background: rgba(255, 255, 255, 0.02);
    }

    .toggle-text {
      font-size: 9px;
      color: rgba(255, 255, 255, 0.7);
    }

    .toggle-switch {
      width: 24px;
      height: 12px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      position: relative;
      transition: background 0.2s ease;
    }

    .toggle-switch.active {
      background: #00f2ff;
    }

    .toggle-switch::after {
      content: '';
      width: 10px;
      height: 10px;
      background: #ffffff;
      border-radius: 50%;
      position: absolute;
      top: 1px;
      left: 1px;
      transition: transform 0.2s ease;
    }

    .toggle-switch.active::after {
      transform: translateX(12px);
    }

    /* Lock Card */
    .lock-card {
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(4, 12, 28, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(0, 242, 255, 0.35);
      border-radius: 8px;
      padding: 14px 16px;
      min-width: 200px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 16px rgba(0, 242, 255, 0.08);
      z-index: 10;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .lock-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(0, 242, 255, 0.15);
      padding-bottom: 6px;
    }

    .lock-callsign {
      font-size: 16px;
      font-weight: 800;
      letter-spacing: 0.06em;
      color: #00f2ff;
    }

    .lock-close {
      background: none;
      border: none;
      color: rgba(0, 242, 255, 0.5);
      font-size: 12px;
      cursor: pointer;
    }

    .lock-close:hover {
      color: #ffffff;
    }

    .lock-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
    }

    .lock-label {
      color: rgba(255, 255, 255, 0.4);
      text-transform: uppercase;
      font-weight: bold;
    }

    .lock-val {
      color: #ffffff;
      font-family: monospace;
    }

    .zoom-overlay {
      position: absolute;
      bottom: 16px;
      right: 16px;
      background: rgba(4, 10, 26, 0.8);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(0, 242, 255, 0.2);
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 9px;
      color: rgba(0, 242, 255, 0.8);
      z-index: 10;
      pointer-events: none;
    }

    .empty-roster {
      font-size: 10px;
      color: rgba(255, 255, 255, 0.3);
      text-align: center;
      margin-top: 40px;
      font-style: italic;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => this._handleResize());
    this.nextAnimationFrame();
  }

  disconnectedCallback() {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    if (this._animationFrameId) {
      cancelAnimationFrame(this._animationFrameId);
      this._animationFrameId = null;
    }
    super.disconnectedCallback();
  }

  firstUpdated() {
    if (this._canvas) {
      this._ctx = this._canvas.getContext('2d');

      // Observe the host element itself so the ResizeObserver fires whenever
      // the host (or any ancestor) resizes — including the initial layout pass.
      // Observing `parentElement` (the fixed-height #a2ui-stage-root, which never
      // resizes again) fired the observer only once before the flex layout of
      // .viewport-wrapper had settled, locking _canvasW/_canvasH at a stale/half
      // size — that's why the scene rendered only in the top vertical half.
      this._resizeObserver?.observe(this);

      // Also observe the shadow-DOM viewport wrapper directly so any internal
      // reflow (e.g. HUD panel toggling) is captured.
      const viewportWrapper = this.shadowRoot?.querySelector('.viewport-wrapper');
      if (viewportWrapper) {
        this._resizeObserver?.observe(viewportWrapper);
      }

      // Immediate best-effort measure, then a rAF-deferred measure so we capture
      // the size after the flex layout has fully settled.
      this._handleResize();
      requestAnimationFrame(() => this._handleResize());
    }
  }

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    if (changedProperties.has('flights')) {
      let flightsParsed = this.flights;
      if (typeof this.flights === 'string') {
        try {
          const parsed = JSON.parse(this.flights);
          flightsParsed = Array.isArray(parsed) ? parsed : (parsed?.flights || []);
        } catch {
          flightsParsed = [];
        }
      } else if (this.flights && typeof this.flights === 'object' && !Array.isArray(this.flights)) {
        flightsParsed = (this.flights as any).flights || [];
      }
      this.flights = Array.isArray(flightsParsed) ? flightsParsed : [];

      // Update trails mapping
      const activeCallsigns = new Set(this.flights.map(f => f.callsign));
      // Prune inactive trails
      for (const cs of this._trails.keys()) {
        if (!activeCallsigns.has(cs)) {
          this._trails.delete(cs);
        }
      }

      // Add points to active trails
      for (const flight of this.flights) {
        const pos = getFlight3DPosition(flight);
        let trail = this._trails.get(flight.callsign);
        if (!trail) {
          trail = [];
          this._trails.set(flight.callsign, trail);
        }
        // Avoid duplicate trailing points if flight is completely stationary
        const last = trail[trail.length - 1];
        if (!last || last.x !== pos.x || last.y !== pos.y || last.z !== pos.z) {
          trail.push({ x: pos.x, y: pos.y, z: pos.z });
          if (trail.length > 50) {
            trail.shift();
          }
        }
      }
    }
  }

  private _handleResize() {
    const viewportWrapper = this.shadowRoot?.querySelector('.viewport-wrapper');
    if (viewportWrapper && this._canvas) {
      const rect = viewportWrapper.getBoundingClientRect();
      // Guard against degenerate sizes — don't lock in a stale/zero size before
      // layout settles (the cause of the top-half-only render).
      if (rect.width < 10 || rect.height < 10) return;
      const dpr = window.devicePixelRatio || 1;
      this._canvasW = rect.width;
      this._canvasH = rect.height;
      // Setting canvas.width/height resets the 2D context transform entirely,
      // so ctx.scale(dpr, dpr) MUST come after these assignments.
      this._canvas.width = rect.width * dpr;
      this._canvas.height = rect.height * dpr;
      if (this._ctx) {
        this._ctx.scale(dpr, dpr);
      }
    }
  }

  // 3D Projection Engine
  private _project(p: Point3D): Point2D {
    const yawRad = (this.cameraYaw) * Math.PI / 180;
    const pitchRad = (this.cameraPitch) * Math.PI / 180;

    let px = p.x;
    let py = p.y;
    let pz = p.z;

    if (this.autoTrack && this.lockedCallsign) {
      const lockedF = this.flights.find(f => f.callsign === this.lockedCallsign);
      if (lockedF) {
        const targetPos = getFlight3DPosition(lockedF);
        px = px - targetPos.x;
        py = py - targetPos.y;
        pz = pz - targetPos.z;
      }
    }

    // Z Elevation exaggeration for tactical clarity (industry-standard 3D TMA representation)
    const verticalExaggeration = 5.0;
    const zScaled = (pz / 6076.12) * verticalExaggeration;

    // 1. Rotate Yaw around Z axis
    const cosY = Math.cos(yawRad);
    const sinY = Math.sin(yawRad);
    const x1 = px * cosY - py * sinY;
    const y1 = px * sinY + py * cosY;
    const z1 = zScaled;

    // 2. Rotate Pitch around horizontal screen X axis
    const cosP = Math.cos(pitchRad);
    const sinP = Math.sin(pitchRad);
    const x2 = x1;
    const y2 = y1 * cosP - z1 * sinP;
    const z2 = y1 * sinP + z1 * cosP;

    // 3. Camera distance scale based on zoom property
    const baseDist = 45;
    const cameraDistance = baseDist * (12 / this.zoom);

    // 4. Perspective Projection division
    const f = Math.min(this._canvasW, this._canvasH) * 0.95;
    const depth = y2 + cameraDistance;
    const scale = depth > 0.5 ? f / depth : f / 0.5;

    return {
      u: this._canvasW / 2 + x2 * scale,
      v: this._canvasH / 2 - z2 * scale,
      depth: y2
    };
  }

  private nextAnimationFrame() {
    this._animationFrameId = requestAnimationFrame(() => {
      if (this.cinematicOrbit && !this._isDragging) {
        this.cameraYaw = (this.cameraYaw + 0.05) % 360;
      }
      this._drawScene();
      this.nextAnimationFrame();
    });
  }

  private _drawScene() {
    const ctx = this._ctx;
    if (!ctx) return;

    // 1. Clear background
    ctx.clearRect(0, 0, this._canvasW, this._canvasH);

    // Update procedural sweep line
    this._radarSweepAngle = (this._radarSweepAngle + 0.015) % (Math.PI * 2);

    // 2. Draw ground terrain/airspace structures
    if (this.showTerrain) {
      this._drawGrid(ctx);
    }

    // 3. Draw ILS glide path landing corridor
    if (this.showGlideSlope) {
      this._drawGlideSlope(ctx);
    }

    // 4. Draw flights, trails, and labels
    this._drawFlightsAndTrails(ctx);

    // 5. Draw digital compass border / horizon
    this._drawHUDHorizon(ctx);
  }

  private _drawGrid(ctx: CanvasRenderingContext2D) {
    const rings = [10, 20, 30]; // radii in NM
    const steps = 36; // radial lines every 10 degrees

    // Draw concentric radar rings projected onto Z = 0
    ctx.lineWidth = 0.5;
    rings.forEach((r, idx) => {
      ctx.strokeStyle = idx === 2 ? 'rgba(0, 242, 255, 0.22)' : 'rgba(0, 242, 255, 0.08)';
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const theta = (i / steps) * Math.PI * 2;
        const pt = this._project({ x: r * Math.cos(theta), y: r * Math.sin(theta), z: 0 });
        if (i === 0) ctx.moveTo(pt.u, pt.v);
        else ctx.lineTo(pt.u, pt.v);
      }
      ctx.stroke();

      // Label rings
      const lblPt = this._project({ x: r * Math.cos(Math.PI / 4), y: r * Math.sin(Math.PI / 4), z: 0 });
      ctx.fillStyle = 'rgba(0, 242, 255, 0.4)';
      ctx.font = '7px monospace';
      ctx.fillText(`${r}NM`, lblPt.u + 2, lblPt.v - 2);
    });

    // Draw axes line crosses
    ctx.strokeStyle = 'rgba(0, 242, 255, 0.06)';
    ctx.lineWidth = 0.5;
    const axises = [
      { start: { x: -30, y: 0, z: 0 }, end: { x: 30, y: 0, z: 0 } },
      { start: { x: 0, y: -30, z: 0 }, end: { x: 0, y: 30, z: 0 } }
    ];
    axises.forEach(ax => {
      const p1 = this._project(ax.start);
      const p2 = this._project(ax.end);
      ctx.beginPath();
      ctx.moveTo(p1.u, p1.v);
      ctx.lineTo(p2.u, p2.v);
      ctx.stroke();
    });

    // Draw cardinal direction points
    const cardinals = [
      { char: 'N', x: 0, y: 32 },
      { char: 'S', x: 0, y: -32 },
      { char: 'E', x: 32, y: 0 },
      { char: 'W', x: -32, y: 0 }
    ];
    ctx.font = 'bold 8px sans-serif';
    ctx.fillStyle = 'rgba(0, 242, 255, 0.55)';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    cardinals.forEach(card => {
      const pt = this._project({ x: card.x, y: card.y, z: 0 });
      ctx.fillText(card.char, pt.u, pt.v);
    });

    // Draw vertical reference cage cylinders to represent the 3D terminal airspace block boundaries
    if (this._showCylinders) {
      ctx.strokeStyle = 'rgba(0, 242, 255, 0.04)';
      ctx.lineWidth = 0.5;
      const tmaPoints = 12;
      const tmaRadius = 30;
      for (let i = 0; i < tmaPoints; i++) {
        const theta = (i / tmaPoints) * Math.PI * 2;
        const cosT = Math.cos(theta);
        const sinT = Math.sin(theta);
        const base = this._project({ x: tmaRadius * cosT, y: tmaRadius * sinT, z: 0 });
        const ceiling = this._project({ x: tmaRadius * cosT, y: tmaRadius * sinT, z: 6000 });
        ctx.beginPath();
        ctx.moveTo(base.u, base.v);
        ctx.lineTo(ceiling.u, ceiling.v);
        ctx.stroke();
      }

      // Draw top-ceiling ring bounding limit
      ctx.strokeStyle = 'rgba(0, 242, 255, 0.06)';
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const theta = (i / steps) * Math.PI * 2;
        const pt = this._project({ x: tmaRadius * Math.cos(theta), y: tmaRadius * Math.sin(theta), z: 6000 });
        if (i === 0) ctx.moveTo(pt.u, pt.v);
        else ctx.lineTo(pt.u, pt.v);
      }
      ctx.stroke();
    }

    // Central airfield indicator (Toulouse LFBO airfield ground marker)
    const hubPt = this._project({ x: 0, y: 0, z: 0 });
    ctx.fillStyle = '#00f2ff';
    ctx.beginPath();
    ctx.arc(hubPt.u, hubPt.v, 1.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = 'rgba(0, 242, 255, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(hubPt.u, hubPt.v, 4, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = 'rgba(0, 242, 255, 0.5)';
    ctx.font = '8px monospace';
    ctx.fillText('LFBO (Toulouse Blagnac)', hubPt.u, hubPt.v + 12);
  }

  private _drawGlideSlope(ctx: CanvasRenderingContext2D) {
    // Runway 32 heading is 320 degrees. Approaching from southeast bearing 140.
    // Bearing 140 is -50 degrees mathematically.
    const thetaApproach = -50 * Math.PI / 180;
    const glideAngle = 3 * Math.PI / 180; // Standard 3-deg glide path
    const maxGlideDistance = 15; // NM

    // 1. Draw glowing landing corridor cone
    const steps = 4; // drawing slices along the final approach course
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = 'rgba(255, 0, 128, 0.16)';

    for (let i = 1; i <= steps; i++) {
      const d = (i / steps) * maxGlideDistance;
      const centerAlt = d * 6076.12 * Math.tan(glideAngle);

      const cx = -d * Math.cos(thetaApproach);
      const cy = -d * Math.sin(thetaApproach);

      // Render outer bounds ellipse at each slice
      const coneRadiusUnits = d * 0.08; // width expands at distance
      const centerPt = this._project({ x: cx, y: cy, z: centerAlt });

      ctx.beginPath();
      for (let j = 0; j <= 24; j++) {
        const phi = (j / 24) * Math.PI * 2;
        // Project points around the center
        const p = this._project({
          x: cx + coneRadiusUnits * Math.cos(phi),
          y: cy + coneRadiusUnits * Math.sin(phi),
          z: centerAlt
        });
        if (j === 0) ctx.moveTo(p.u, p.v);
        else ctx.lineTo(p.u, p.v);
      }
      ctx.stroke();

      // Label approach segment
      if (i === steps) {
        ctx.fillStyle = 'rgba(255, 0, 128, 0.4)';
        ctx.font = '7px monospace';
        ctx.fillText(`ILS 32 APPROACH CONE`, centerPt.u, centerPt.v - 8);
      }
    }

    // 2. Draw central Localizer/Glide slope center line
    const start3D = { x: 0, y: 0, z: 0 };
    const endAlt = maxGlideDistance * 6076.12 * Math.tan(glideAngle);
    const end3D = {
      x: -maxGlideDistance * Math.cos(thetaApproach),
      y: -maxGlideDistance * Math.sin(thetaApproach),
      z: endAlt
    };

    const pStart = this._project(start3D);
    const pEnd = this._project(end3D);

    ctx.strokeStyle = 'rgba(255, 0, 128, 0.4)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(pStart.u, pStart.v);
    ctx.lineTo(pEnd.u, pEnd.v);
    ctx.stroke();
    ctx.setLineDash([]); // clear dash
  }

  private _drawFlightsAndTrails(ctx: CanvasRenderingContext2D) {
    this.flights.forEach(f => {
      const pos3D = getFlight3DPosition(f);
      const pos2D = this._project(pos3D);
      const isLocked = f.callsign === this.lockedCallsign;

      // Color based on vertical rate (emerald descending, amber climbing, cyan level)
      let blipColor = '#00f2ff';
      if (f.vrate < -250) blipColor = '#00ff88'; // descending
      else if (f.vrate > 250) blipColor = '#ffd60a'; // climbing

      // 1. Draw glowing trail history
      if (this._showTrails) {
        const trail = this._trails.get(f.callsign);
        if (trail && trail.length > 1) {
          ctx.lineWidth = isLocked ? 1.5 : 0.8;
          for (let i = 0; i < trail.length - 1; i++) {
            const pt1 = this._project(trail[i]);
            const pt2 = this._project(trail[i+1]);

            // Gradient fade: older segments are highly transparent
            const opacity = (i / trail.length) * (isLocked ? 0.8 : 0.5);
            ctx.strokeStyle = blipColor;
            ctx.globalAlpha = opacity;
            ctx.beginPath();
            ctx.moveTo(pt1.u, pt1.v);
            ctx.lineTo(pt2.u, pt2.v);
            ctx.stroke();
          }
          ctx.globalAlpha = 1.0; // reset opacity
        }
      }

      // 2. Draw tactical altitude drop strings linking airplane down to base grid
      if (this._showAltDropLines) {
        const groundPt = this._project({ x: pos3D.x, y: pos3D.y, z: 0 });
        ctx.strokeStyle = isLocked ? 'rgba(0, 242, 255, 0.45)' : 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 0.5;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.moveTo(pos2D.u, pos2D.v);
        ctx.lineTo(groundPt.u, groundPt.v);
        ctx.stroke();
        ctx.setLineDash([]); // reset

        // Small circle on ground projection
        ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.beginPath();
        ctx.arc(groundPt.u, groundPt.v, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // 3. Draw aircraft icon (sleek premium 3D vector delta wing symbol)
      ctx.save();
      ctx.translate(pos2D.u, pos2D.v);

      // Add gorgeous premium neon glow filters for locked targets
      if (isLocked) {
        ctx.shadowBlur = 10;
        ctx.shadowColor = blipColor;
      }

      ctx.fillStyle = blipColor;
      ctx.beginPath();
      // Draw a neat delta symbol oriented along the heading angle
      // We compensate for camera yaw so the aircraft rotates visually inside the orbit scene
      const localAngle = pos3D.heading - (this.cameraYaw * Math.PI / 180);
      const size = isLocked ? 5 : 4.2;

      ctx.moveTo(size * 1.5 * Math.cos(localAngle), size * 1.5 * Math.sin(localAngle));
      ctx.lineTo(size * Math.cos(localAngle + 2.4), size * Math.sin(localAngle + 2.4));
      ctx.lineTo(size * 0.4 * Math.cos(localAngle + Math.PI), size * 0.4 * Math.sin(localAngle + Math.PI));
      ctx.lineTo(size * Math.cos(localAngle - 2.4), size * Math.sin(localAngle - 2.4));
      ctx.closePath();
      ctx.fill();

      // Additional concentric ring for locked target
      if (isLocked) {
        ctx.strokeStyle = blipColor;
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.arc(0, 0, 9, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();

      // 4. Tactical Data tags next to flight
      ctx.fillStyle = isLocked ? '#ffffff' : 'rgba(255, 255, 255, 0.82)';
      ctx.font = isLocked ? 'bold 8px monospace' : '7.5px monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';

      const offsetU = isLocked ? 12 : 9;
      const fl = Math.round(f.altitude * 3.28084 / 100).toString().padStart(3, '0');
      const textTag = `${f.callsign}\nFL${fl} ${f.speed}KT`;

      const lines = textTag.split('\n');
      lines.forEach((line, lineIdx) => {
        ctx.fillText(line, pos2D.u + offsetU, pos2D.v - 6 + (lineIdx * 8.5));
      });
    });
  }

  private _drawHUDHorizon(ctx: CanvasRenderingContext2D) {
    // Clean digital border overlays representing spatial cockpit metrics
    ctx.strokeStyle = 'rgba(0, 242, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.strokeRect(10, 10, this._canvasW - 20, this._canvasH - 20);

    // Decorative corner ticks
    const tickLen = 6;
    ctx.strokeStyle = '#00f2ff';
    ctx.lineWidth = 1.2;

    const corners = [
      // Top-Left
      { x: 10, y: 10, dx: 1, dy: 1 },
      // Top-Right
      { x: this._canvasW - 10, y: 10, dx: -1, dy: 1 },
      // Bottom-Left
      { x: 10, y: this._canvasH - 10, dx: 1, dy: -1 },
      // Bottom-Right
      { x: this._canvasW - 10, y: this._canvasH - 10, dx: -1, dy: -1 }
    ];

    corners.forEach(c => {
      ctx.beginPath();
      ctx.moveTo(c.x, c.y + c.dy * tickLen);
      ctx.lineTo(c.x, c.y);
      ctx.lineTo(c.x + c.dx * tickLen, c.y);
      ctx.stroke();
    });

    // Pitch & Yaw digital tickers
    ctx.fillStyle = 'rgba(0, 242, 255, 0.45)';
    ctx.font = '7.5px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`PITCH: ${Math.round(this.cameraPitch)}°`, this._canvasW - 16, this._canvasH - 22);
    ctx.fillText(`YAW: ${Math.round(this.cameraYaw)}°`, this._canvasW - 16, this._canvasH - 13);
  }

  // Interaction handlers
  private _onPointerDown(e: PointerEvent) {
    this._isDragging = true;
    this._lastPointerX = e.clientX;
    this._lastPointerY = e.clientY;
    this._canvas.setPointerCapture(e.pointerId);
  }

  private _onPointerMove(e: PointerEvent) {
    if (!this._isDragging) return;

    const deltaX = e.clientX - this._lastPointerX;
    const deltaY = e.clientY - this._lastPointerY;

    this._lastPointerX = e.clientX;
    this._lastPointerY = e.clientY;

    // Orbit Yaw (orbiting around Z, horizontal pointer movement updates Yaw)
    let newYaw = this.cameraYaw - deltaX * 0.4;
    if (newYaw < 0) newYaw += 360;
    if (newYaw >= 360) newYaw -= 360;
    this.cameraYaw = newYaw;

    // Orbit Pitch (vertical tilt, vertical pointer movement updates Pitch)
    // Clamped strictly between 5 degrees (almost horizontal profile) and 85 degrees (almost flat top-down)
    const newPitch = Math.min(Math.max(5, this.cameraPitch + deltaY * 0.4), 85);
    this.cameraPitch = newPitch;

    // Dispatch angle updates back to backend to keep states synchronized
    this.dispatchEvent(new CustomEvent('camera-rotate', {
      detail: { pitch: this.cameraPitch, yaw: this.cameraYaw },
      bubbles: true,
      composed: true
    }));
  }

  private _onPointerUp(e: PointerEvent) {
    if (this._isDragging) {
      this._isDragging = false;
      this._canvas.releasePointerCapture(e.pointerId);
    }
  }

  private _setPresetAngle(preset: 'top' | 'iso' | 'profile') {
    if (preset === 'top') {
      this.cameraPitch = 85;
      this.cameraYaw = 45;
    } else if (preset === 'iso') {
      this.cameraPitch = 35;
      this.cameraYaw = 45;
    } else if (preset === 'profile') {
      this.cameraPitch = 8;
      this.cameraYaw = 135;
    }
    this.dispatchEvent(new CustomEvent('camera-rotate', {
      detail: { pitch: this.cameraPitch, yaw: this.cameraYaw },
      bubbles: true,
      composed: true
    }));
  }

  private _lockFlight(callsign: string) {
    this.dispatchEvent(new CustomEvent('target-lock', {
      detail: { callsign },
      bubbles: true,
      composed: true
    }));
  }

  private _clearLock() {
    this.dispatchEvent(new CustomEvent('target-lock', {
      detail: { callsign: '' },
      bubbles: true,
      composed: true
    }));
  }

  private _toggleControl(control: 'lines' | 'trails' | 'cylinders' | 'orbit' | 'track') {
    if (control === 'lines') {
      this._showAltDropLines = !this._showAltDropLines;
    } else if (control === 'trails') {
      this._showTrails = !this._showTrails;
    } else if (control === 'cylinders') {
      this._showCylinders = !this._showCylinders;
    } else if (control === 'orbit') {
      this.cinematicOrbit = !this.cinematicOrbit;
    } else if (control === 'track') {
      this.autoTrack = !this.autoTrack;
    }
  }

  private _flVal(altitude: number): number {
    return Math.round(altitude * 3.28084 / 100);
  }

  render() {
    const lockedFlight = this.flights.find(f => f.callsign === this.lockedCallsign);

    return html`
      <div class="tma-deck-container">
        <!-- 3D Canvas Space Viewport -->
        <div class="viewport-wrapper">
          <div class="hud-title-bar">
            <h1 class="hud-title">
              <span class="live-pulse"></span>
              TLS TMA Tactical Airspace
            </h1>
            <div class="hud-subtitle">3D Command Deck · A2UI v0.8 Core</div>
          </div>

          <div class="hud-controls-overlay">
            <!-- Preset Angles -->
            <div class="controls-group">
              <span class="controls-label">Orbit Presets</span>
              <div class="preset-row">
                <button class="control-btn" @click="${() => this._setPresetAngle('top')}">Top Radar</button>
                <button class="control-btn" @click="${() => this._setPresetAngle('iso')}">3D Iso</button>
                <button class="control-btn" @click="${() => this._setPresetAngle('profile')}">Profile</button>
              </div>
            </div>

            <!-- Visual Toggles -->
            <div class="controls-group">
              <span class="controls-label">Visual Overlays</span>
              
              <div class="toggle-control" @click="${() => this._toggleControl('lines')}">
                <span class="toggle-text">Altitude drop lines</span>
                <div class="toggle-switch ${this._showAltDropLines ? 'active' : ''}"></div>
              </div>

              <div class="toggle-control" @click="${() => this._toggleControl('trails')}">
                <span class="toggle-text">Historical 3D trails</span>
                <div class="toggle-switch ${this._showTrails ? 'active' : ''}"></div>
              </div>

              <div class="toggle-control" @click="${() => this._toggleControl('cylinders')}">
                <span class="toggle-text">Airspace ceiling boundary</span>
                <div class="toggle-switch ${this._showCylinders ? 'active' : ''}"></div>
              </div>
            </div>
          </div>

          <canvas
            @pointerdown="${this._onPointerDown}"
            @pointermove="${this._onPointerMove}"
            @pointerup="${this._onPointerUp}"
          ></canvas>

          <!-- Floating details card for currently locked flight -->
          ${lockedFlight ? html`
            <div class="lock-card">
              <div class="lock-card-header">
                <span class="lock-callsign">${lockedFlight.callsign}</span>
                <button class="lock-close" @click="${this._clearLock}">✕</button>
              </div>
              <div class="lock-row">
                <span class="lock-label">Altitude</span>
                <span class="lock-val">FL${this._flVal(lockedFlight.altitude).toString().padStart(3, '0')} (${lockedFlight.altitude.toLocaleString()}m)</span>
              </div>
              <div class="lock-row">
                <span class="lock-label">Speed</span>
                <span class="lock-val">${lockedFlight.speed} KT</span>
              </div>
              <div class="lock-row">
                <span class="lock-label">V. Rate</span>
                <span class="lock-val" style="color: ${lockedFlight.vrate < -250 ? '#00ff88' : (lockedFlight.vrate > 250 ? '#ffd60a' : '#00f2ff')}">
                  ${lockedFlight.vrate < -250 ? '▼' : (lockedFlight.vrate > 250 ? '▲' : '—')} ${Math.abs(lockedFlight.vrate)} FPM
                </span>
              </div>
              ${lockedFlight.origin ? html`
                <div class="lock-row">
                  <span class="lock-label">Origin</span>
                  <span class="lock-val">${lockedFlight.origin}</span>
                </div>
              ` : ''}
              ${lockedFlight.destination ? html`
                <div class="lock-row">
                  <span class="lock-label">Destination</span>
                  <span class="lock-val">${lockedFlight.destination}</span>
                </div>
              ` : ''}
            </div>
          ` : ''}

          <!-- Zoom Display overlay -->
          <div class="zoom-overlay">Range: ${this.zoom.toFixed(1)} NM</div>
        </div>

        <!-- HUD Side Panel with Traffic Roster -->
        <div class="hud-side-panel">
          <div class="panel-tabs">
            <button class="tab-btn ${this._activeTab === '3d' ? 'active' : ''}" @click="${() => this._activeTab = '3d'}">System</button>
            <button class="tab-btn ${this._activeTab === 'traffic' ? 'active' : ''}" @click="${() => this._activeTab = 'traffic'}">Traffic (${this.flights.length})</button>
          </div>

          <div class="panel-content">
            ${this._activeTab === '3d' ? html`
              <!-- System Metrics & Telemetry -->
              <div class="controls-label" style="margin-top:8px;">Command Deck Sensors</div>
              <div class="flight-row" style="cursor:default;">
                <div class="flight-row-left">
                  <span class="flight-row-callsign" style="color:#00f2ff;">ILS Runway 32</span>
                  <span class="flight-row-route">Glidepath: 3.00° Incl.</span>
                </div>
                <div class="flight-row-right">
                  <span class="flight-row-fl" style="color:#00ff88; font-weight:bold;">ACTIVE</span>
                </div>
              </div>
              <div class="flight-row" style="cursor:default;">
                <div class="flight-row-left">
                  <span class="flight-row-callsign">TMA Sector Alpha</span>
                  <span class="flight-row-route">Ceiling boundary: 6000m</span>
                </div>
                <div class="flight-row-right">
                  <span class="flight-row-fl" style="color:#ffd60a;">AUTO</span>
                </div>
              </div>

              <div class="controls-label" style="margin-top:12px;">3D Camera Modes</div>
              <div class="toggle-control" @click="${() => this._toggleControl('orbit')}">
                <span class="toggle-text">Cinematic Auto-Orbit</span>
                <div class="toggle-switch ${this.cinematicOrbit ? 'active' : ''}"></div>
              </div>
              <div class="toggle-control" @click="${() => this._toggleControl('track')}">
                <span class="toggle-text">Auto-Track Target Lock</span>
                <div class="toggle-switch ${this.autoTrack ? 'active' : ''}"></div>
              </div>

              <div class="controls-label" style="margin-top:12px;">3D Viewport Orbit controls</div>
              <div style="font-size:9.5px; color:rgba(255,255,255,0.6); line-height:1.4; padding: 4px 6px;">
                • Click and drag on viewport to rotate Yaw and Pitch.<br>
                • Change orbit presets from top-right toolbar.<br>
                • Click on targets to lock and inspect telemetry.
              </div>
            ` : html`
              <!-- Traffic Roster -->
              ${this.flights.length === 0 ? html`
                <div class="empty-roster">No contacts in radar sector</div>
              ` : this.flights.map(f => {
                const isLocked = f.callsign === this.lockedCallsign;
                let vrateColor = '#00f2ff';
                let vrateSym = '—';
                if (f.vrate < -250) {
                  vrateColor = '#00ff88';
                  vrateSym = '▼';
                } else if (f.vrate > 250) {
                  vrateColor = '#ffd60a';
                  vrateSym = '▲';
                }
                return html`
                  <div
                    class="flight-row ${isLocked ? 'locked' : ''}"
                    @click="${() => this._lockFlight(f.callsign)}"
                  >
                    <div class="flight-row-left">
                      <span class="flight-row-callsign" style="color: ${vrateColor};">${f.callsign}</span>
                      <span class="flight-row-route">${f.origin || '??'} ➔ ${f.destination || '??'}</span>
                    </div>
                    <div class="flight-row-right">
                      <span class="flight-row-fl">FL${this._flVal(f.altitude).toString().padStart(3, '0')}</span>
                      <span class="flight-row-vrate" style="color: ${vrateColor};">${vrateSym}</span>
                    </div>
                  </div>
                `;
              })}
            `}
          </div>
        </div>
      </div>
    `;
  }
}
