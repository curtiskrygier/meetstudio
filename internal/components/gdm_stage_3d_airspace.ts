import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ScenePoint, SceneLink } from './gdm_stage_3d_scene';

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
  // Embedded-mode: hide ALL internal chrome (title bar, side panel, controls,
  // lock card, zoom overlay) so the molecule contributes only the 3D scene to
  // an outer composition. Use when wrapping in a composed deck where the outer
  // chrome (header, sidebar, captions) owns the UI.
  @property({ type: Boolean, reflect: true }) compact = false;

  @state() private _activeTab = '3d'; // side panels: '3d', 'traffic'
  @state() private _showAltDropLines = true;
  @state() private _showTrails = true;
  @state() private _showCylinders = true;

  private _trails = new Map<string, Point3D[]>();

  static styles = css`
    /* Embedded mode: hide every internal chrome element so the molecule
       contributes only the 3D scene to an outer composition. The flex
       .viewport-wrapper has flex:1 and the .hud-side-panel is display:none,
       so the scene expands to fill the whole host. */
    :host([compact]) .hud-title-bar,
    :host([compact]) .hud-side-panel,
    :host([compact]) .hud-controls-overlay,
    :host([compact]) .lock-card,
    :host([compact]) .zoom-overlay { display: none !important; }

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

    gdm-3d-scene {
      display: block;
      width: 100%;
      height: 100%;
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

  private _mapToScenePoint(pos: { x: number; y: number; z: number }): { x: number; y: number; z: number } {
    const scaleXY = 3.5;
    // Map 0..6000 feet to 12..48 units in scene space to clear terrain waves
    const zScene = 12 + (pos.z / 6000) * 36;
    return {
      x: pos.x * scaleXY,
      y: pos.y * scaleXY,
      z: zScene
    };
  }

  private _getPoints(): ScenePoint[] {
    const pointsList: ScenePoint[] = [];

    // 1. Airfield LFBO ground marker
    pointsList.push({
      id: 'LFBO',
      x: 0,
      y: 0,
      z: 11,
      color: '#00f2ff',
      label: 'LFBO (Toulouse Blagnac)',
      glyph: 'square',
      size: 7
    });

    // 2. Approach waypoints along the final glide slope approach
    const thetaApproach = -50 * Math.PI / 180;
    const glideAngle = 3 * Math.PI / 180;
    const maxGlideDistance = 15;
    const steps = 4;

    for (let i = 1; i <= steps; i++) {
      const d = (i / steps) * maxGlideDistance;
      const centerAlt = d * 6076.12 * Math.tan(glideAngle);
      const cx = -d * Math.cos(thetaApproach);
      const cy = -d * Math.sin(thetaApproach);

      const scenePos = this._mapToScenePoint({ x: cx, y: cy, z: centerAlt });
      pointsList.push({
        id: `ILS-WP-${i}`,
        x: scenePos.x,
        y: scenePos.y,
        z: scenePos.z,
        color: 'rgba(255, 0, 128, 0.45)',
        label: i === steps ? 'ILS 32 APPROACH PATH' : `ILS-WP-${i}`,
        glyph: 'diamond',
        size: 5
      });
    }

    // 3. Flight contacts
    this.flights.forEach(f => {
      const pos3D = getFlight3DPosition(f);
      const scenePos = this._mapToScenePoint(pos3D);
      const isLocked = f.callsign === this.lockedCallsign;

      let blipColor = '#00f2ff';
      if (f.vrate < -250) blipColor = '#00ff88'; // descending (emerald)
      else if (f.vrate > 250) blipColor = '#ffd60a'; // climbing (amber)

      // Convert radians heading to degrees clockwise from North (+Y)
      const headingDeg = 90 - (pos3D.heading * 180 / Math.PI);

      let mappedTrail: Array<{ x: number; y: number; z: number }> | undefined = undefined;
      if (this._showTrails) {
        const trail = this._trails.get(f.callsign);
        if (trail) {
          mappedTrail = trail.map(pt => this._mapToScenePoint(pt));
        }
      }

      pointsList.push({
        id: f.callsign,
        x: scenePos.x,
        y: scenePos.y,
        z: scenePos.z,
        color: blipColor,
        label: f.callsign,
        glyph: isLocked ? 'aircraft' : 'circle',
        size: isLocked ? 10 : 7,
        heading: headingDeg,
        trail: mappedTrail
      });

      // 4. Altitude drop-lines representation (we can add a ground anchor point and link to it)
      if (this._showAltDropLines) {
        const groundId = `ground-${f.callsign}`;
        pointsList.push({
          id: groundId,
          x: scenePos.x,
          y: scenePos.y,
          z: 0,
          color: 'rgba(255, 255, 255, 0.15)',
          glyph: 'circle',
          size: 2
        });
      }
    });

    return pointsList;
  }

  private _getLinks(): SceneLink[] {
    const linksList: SceneLink[] = [];

    // 1. ILS Approach Corridor Links
    if (this.showGlideSlope) {
      const steps = 4;
      for (let i = 1; i <= steps; i++) {
        const fromId = `ILS-WP-${i}`;
        const toId = i === 1 ? 'LFBO' : `ILS-WP-${i-1}`;
        linksList.push({
          from: fromId,
          to: toId,
          color: 'rgba(255, 0, 128, 0.4)'
        });
      }
    }

    // 2. Flight altitude drop strings represented as Links
    if (this._showAltDropLines) {
      this.flights.forEach(f => {
        linksList.push({
          from: f.callsign,
          to: `ground-${f.callsign}`,
          color: f.callsign === this.lockedCallsign ? 'rgba(0, 242, 255, 0.35)' : 'rgba(255, 255, 255, 0.08)'
        });
      });
    }

    return linksList;
  }

  private _getCamera() {
    return {
      pitch: this.cameraPitch,
      yaw: this.cameraYaw,
      zoom: this.zoom / 10.0,
      autoOrbit: this.cinematicOrbit,
      lockTo: this.autoTrack && this.lockedCallsign ? this.lockedCallsign : null
    };
  }

  private _onCameraChange(e: CustomEvent) {
    const cam = e.detail.camera;
    if (cam) {
      if (typeof cam.pitch === 'number') {
        this.cameraPitch = cam.pitch;
      }
      if (typeof cam.yaw === 'number') {
        this.cameraYaw = cam.yaw;
      }
      if (typeof cam.zoom === 'number') {
        this.zoom = cam.zoom * 10.0;
      }

      this.dispatchEvent(new CustomEvent('camera-rotate', {
        detail: { pitch: this.cameraPitch, yaw: this.cameraYaw },
        bubbles: true,
        composed: true
      }));
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
        <!-- 3D Canvas Space Viewport via nested gdm-3d-scene molecule -->
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
                <span class="toggle-text">Airspace boundary</span>
                <div class="toggle-switch ${this._showCylinders ? 'active' : ''}"></div>
              </div>
            </div>
          </div>

          <gdm-3d-scene
            .points="${this._getPoints()}"
            .links="${this._getLinks()}"
            .camera="${this._getCamera()}"
            .terrain="${this.showTerrain}"
            .grid="${this._showCylinders}"
            .fog="${this.showTerrain}"
            .compact="${this.compact}"
            @camera-change="${this._onCameraChange}"
          ></gdm-3d-scene>

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

declare global {
  interface HTMLElementTagNameMap {
    'gdm-3d-airspace': GdmStage3DAirspace;
  }
}
