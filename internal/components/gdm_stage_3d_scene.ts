import { LitElement, css, html } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';

export interface ScenePoint {
  id: string;
  x: number;
  y: number;
  z: number;
  color?: string;
  label?: string;
  glyph?: 'circle' | 'square' | 'diamond' | 'triangle' | 'airplane' | 'aircraft' | 'arrow';
  size?: number;
  heading?: number; // In degrees, clockwise from North (+Y)
  trail?: Array<{ x: number; y: number; z: number }>;
}

export interface SceneLink {
  from: string;
  to: string;
  color?: string;
}

export interface SceneCamera {
  pitch?: number;      // Degrees (5 to 85)
  yaw?: number;        // Degrees (0 to 360)
  zoom?: number;       // Scale factor (typically 0.5 to 10)
  fov?: number;        // Focal length/Field of view in pixels
  autoOrbit?: boolean; // Toggles automated camera slow rotation
  lockTo?: string | ScenePoint | null; // Point ID or point reference to lock camera target on
}

@customElement('gdm-3d-scene')
export class GdmStage3DScene extends LitElement {
  @property({ type: Array }) points: ScenePoint[] = [];
  @property({ type: Array }) links: SceneLink[] = [];
  @property({ type: Object }) camera: SceneCamera = {};
  @property({ type: Boolean }) terrain = true;
  @property({ type: Boolean }) grid = true;
  @property({ type: Boolean }) fog = true;

  @state() private _canvasW = 400;
  @state() private _canvasH = 400;

  @query('canvas') private _canvas!: HTMLCanvasElement;

  private _ctx: CanvasRenderingContext2D | null = null;
  private _animationFrameId: number | null = null;
  private _resizeObserver: ResizeObserver | null = null;
  private _trails = new Map<string, Array<{ x: number; y: number; z: number }>>();

  // Orbit drag interaction state
  private _isDragging = false;
  private _lastPointerX = 0;
  private _lastPointerY = 0;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      user-select: none;
      background: radial-gradient(circle at center, #050b1d 0%, #02040c 100%);
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }

    .viewport-wrapper {
      width: 100%;
      height: 100%;
      position: relative;
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
      cursor: grab;
    }

    canvas:active {
      cursor: grabbing;
    }

    /* Premium Futuristic Tactical HUD Info Overlays */
    .hud-overlay {
      position: absolute;
      top: 16px;
      left: 16px;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 5;
    }

    .hud-title {
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #00f2ff;
      text-shadow: 0 0 10px rgba(0, 242, 255, 0.4);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .hud-subtitle {
      font-size: 9px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.45);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .live-pulse {
      width: 6px;
      height: 6px;
      background: #00ff88;
      border-radius: 50%;
      box-shadow: 0 0 8px #00ff88;
      display: inline-block;
      animation: pulse 1.2s infinite alternate;
    }

    @keyframes pulse {
      0% { transform: scale(0.8); opacity: 0.5; }
      100% { transform: scale(1.2); opacity: 1; }
    }

    .camera-hud {
      position: absolute;
      bottom: 16px;
      right: 16px;
      background: rgba(4, 10, 26, 0.75);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(0, 242, 255, 0.15);
      border-radius: 6px;
      padding: 8px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      z-index: 5;
      pointer-events: none;
    }

    .hud-row {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      font-size: 8.5px;
      color: rgba(255, 255, 255, 0.6);
      text-transform: uppercase;
    }

    .hud-value {
      color: #00f2ff;
      font-weight: bold;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => this._handleResize());
    this._startLoop();
  }

  disconnectedCallback() {
    if (this._animationFrameId) {
      cancelAnimationFrame(this._animationFrameId);
      this._animationFrameId = null;
    }
    this._resizeObserver?.disconnect();
    super.disconnectedCallback();
  }

  firstUpdated() {
    if (this._canvas) {
      this._ctx = this._canvas.getContext('2d');
      this._resizeObserver?.observe(this);
      
      const viewportWrapper = this.shadowRoot?.querySelector('.viewport-wrapper');
      if (viewportWrapper) {
        this._resizeObserver?.observe(viewportWrapper);
      }

      this._handleResize();
      requestAnimationFrame(() => this._handleResize());
    }
  }

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    if (changedProperties.has('points')) {
      let ptsParsed = this.points;
      if (typeof this.points === 'string') {
        try {
          ptsParsed = JSON.parse(this.points);
        } catch {
          ptsParsed = [];
        }
      }
      this.points = Array.isArray(ptsParsed) ? ptsParsed : [];

      // Update local trail caches
      const activeIds = new Set(this.points.map(p => p.id));
      
      // Clean up stale trails
      for (const id of this._trails.keys()) {
        if (!activeIds.has(id)) {
          this._trails.delete(id);
        }
      }

      // Add newest locations to local trails (up to 25 historical points)
      for (const pt of this.points) {
        if (!pt.id) continue;
        
        // If the point already has a trail specified, we can optionally use that
        if (pt.trail && Array.isArray(pt.trail)) {
          this._trails.set(pt.id, pt.trail);
          continue;
        }

        let trail = this._trails.get(pt.id);
        if (!trail) {
          trail = [];
          this._trails.set(pt.id, trail);
        }

        const last = trail[trail.length - 1];
        if (!last || last.x !== pt.x || last.y !== pt.y || last.z !== pt.z) {
          trail.push({ x: pt.x, y: pt.y, z: pt.z });
          if (trail.length > 25) {
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
      if (rect.width < 10 || rect.height < 10) return;
      
      const dpr = window.devicePixelRatio || 1;
      this._canvasW = rect.width;
      this._canvasH = rect.height;
      
      this._canvas.width = rect.width * dpr;
      this._canvas.height = rect.height * dpr;
      
      if (this._ctx) {
        this._ctx.scale(dpr, dpr);
      }
    }
  }

  private _startLoop() {
    const loop = () => {
      // Handle camera auto orbit rotation
      if (this.camera.autoOrbit && !this._isDragging) {
        const currentYaw = this.camera.yaw ?? 45;
        this.camera = {
          ...this.camera,
          yaw: (currentYaw + 0.12) % 360
        };
      }

      this._drawScene();
      this._animationFrameId = requestAnimationFrame(loop);
    };
    this._animationFrameId = requestAnimationFrame(loop);
  }

  // Camera distance calculation
  private _getCameraDistance(): number {
    const zoom = this.camera.zoom ?? 1.0;
    const baseDistance = 300;
    return baseDistance / zoom;
  }

  // True perspective 3D projection mathematical system
  private _project(p: { x: number; y: number; z: number }): { u: number; v: number; depth: number } {
    const yawRad = (this.camera.yaw ?? 45) * Math.PI / 180;
    const pitchRad = (this.camera.pitch ?? 35) * Math.PI / 180;
    const fov = this.camera.fov ?? 400;

    // Resolve camera/auto-tracking lock target
    let tx = 0;
    let ty = 0;
    let tz = 0;

    if (this.camera.lockTo) {
      let lockPoint: any = null;
      if (typeof this.camera.lockTo === 'string') {
        lockPoint = this.points.find(pt => pt.id === this.camera.lockTo);
      } else if (typeof this.camera.lockTo === 'object') {
        lockPoint = this.camera.lockTo;
      }
      if (lockPoint) {
        tx = lockPoint.x;
        ty = lockPoint.y;
        tz = lockPoint.z;
      }
    }

    // Translate to target coordinate space
    const dx = p.x - tx;
    const dy = p.y - ty;
    const dz = p.z - tz;

    // 1. Yaw rotation around vertical axis (Z-axis)
    const cosY = Math.cos(yawRad);
    const sinY = Math.sin(yawRad);
    const x1 = dx * cosY - dy * sinY;
    const y1 = dx * sinY + dy * cosY;
    const z1 = dz;

    // 2. Pitch rotation around screen horizontal axis (X-axis)
    const cosP = Math.cos(pitchRad);
    const sinP = Math.sin(pitchRad);
    const x2 = x1;
    const y2 = y1 * cosP - z1 * sinP;
    const z2 = y1 * sinP + z1 * cosP;

    // 3. Translate along camera look direction by camera distance
    const cameraDistance = this._getCameraDistance();
    const zc = y2 + cameraDistance;

    // If point is behind the camera (or too close), return coordinate with negative depth
    if (zc <= 0.1) {
      return { u: 0, v: 0, depth: zc };
    }

    // 4. Perspective Projection Divide
    const u = this._canvasW / 2 + (x2 * fov) / zc;
    const v = this._canvasH / 2 - (z2 * fov) / zc;

    return { u, v, depth: zc };
  }

  // Get fog atmospheric perspective opacity based on camera-space depth
  private _getFogOpacity(zc: number, baseOpacity = 1.0): number {
    if (!this.fog) return baseOpacity;
    const D = this._getCameraDistance();
    const minZ = D * 0.45;
    const maxZ = D * 2.3;
    const fogFactor = Math.max(0, Math.min(1, 1 - (zc - minZ) / (maxZ - minZ)));
    return baseOpacity * fogFactor;
  }

  // Slowly animating 3D heightfield height generator for scanning effect
  private _getTerrainHeight(x: number, y: number): number {
    const r = Math.sqrt(x * x + y * y);
    const animTime = Date.now() * 0.0013;
    const baseWave = 14 * Math.sin(x * 0.025) * Math.cos(y * 0.025);
    const movingWave = 5 * Math.sin(r * 0.05 - animTime * 1.5);
    const details = 2.5 * Math.cos((x + y) * 0.075 + animTime * 0.7);
    return baseWave + movingWave + details;
  }

  // Draw Scene Frame
  private _drawScene() {
    const ctx = this._ctx;
    if (!ctx) return;

    // 1. Clear background
    ctx.clearRect(0, 0, this._canvasW, this._canvasH);

    // 2. Assemble 3D primitives to sort with Painter's Algorithm
    const primitives: any[] = [];

    // A. Generate Standard Grid Line Segments at Z=0
    if (this.grid) {
      const gridRange = 150;
      const gridStep = 25;
      
      // Lines along constant X
      for (let x = -gridRange; x <= gridRange; x += gridStep) {
        for (let y = -gridRange; y < gridRange; y += gridStep) {
          const p1 = { x, y, z: 0 };
          const p2 = { x, y: y + gridStep, z: 0 };
          const proj1 = this._project(p1);
          const proj2 = this._project(p2);
          if (proj1.depth > 0.1 && proj2.depth > 0.1) {
            primitives.push({
              type: 'grid_line',
              p1: proj1,
              p2: proj2,
              zc: (proj1.depth + proj2.depth) / 2,
              color: 'rgba(0, 242, 255, 0.10)'
            });
          }
        }
      }
      // Lines along constant Y
      for (let y = -gridRange; y <= gridRange; y += gridStep) {
        for (let x = -gridRange; x < gridRange; x += gridStep) {
          const p1 = { x, y, z: 0 };
          const p2 = { x: x + gridStep, y, z: 0 };
          const proj1 = this._project(p1);
          const proj2 = this._project(p2);
          if (proj1.depth > 0.1 && proj2.depth > 0.1) {
            primitives.push({
              type: 'grid_line',
              p1: proj1,
              p2: proj2,
              zc: (proj1.depth + proj2.depth) / 2,
              color: 'rgba(0, 242, 255, 0.10)'
            });
          }
        }
      }

      // Draw concentric radar ring primitives for extra premium styling
      const radarRings = [40, 80, 120];
      const radialSteps = 24;
      radarRings.forEach(radius => {
        for (let i = 0; i < radialSteps; i++) {
          const theta1 = (i / radialSteps) * Math.PI * 2;
          const theta2 = ((i + 1) / radialSteps) * Math.PI * 2;
          const p1 = { x: radius * Math.cos(theta1), y: radius * Math.sin(theta1), z: 0 };
          const p2 = { x: radius * Math.cos(theta2), y: radius * Math.sin(theta2), z: 0 };
          
          const proj1 = this._project(p1);
          const proj2 = this._project(p2);
          if (proj1.depth > 0.1 && proj2.depth > 0.1) {
            primitives.push({
              type: 'grid_line',
              p1: proj1,
              p2: proj2,
              zc: (proj1.depth + proj2.depth) / 2,
              color: 'rgba(0, 242, 255, 0.08)',
              isRing: true
            });
          }
        }
      });
    }

    // B. Generate Shaded Terrain Heightfield Quads
    if (this.terrain) {
      const terrRange = 140;
      const terrStep = 20; // 15 to 20 grid spacing ensures beautiful density & optimal sorting speed
      
      for (let x = -terrRange; x < terrRange; x += terrStep) {
        for (let y = -terrRange; y < terrRange; y += terrStep) {
          const v00 = { x, y, z: this._getTerrainHeight(x, y) };
          const v10 = { x: x + terrStep, y, z: this._getTerrainHeight(x + terrStep, y) };
          const v11 = { x: x + terrStep, y: y + terrStep, z: this._getTerrainHeight(x + terrStep, y + terrStep) };
          const v01 = { x, y: y + terrStep, z: this._getTerrainHeight(x, y + terrStep) };

          const p00 = this._project(v00);
          const p10 = this._project(v10);
          const p11 = this._project(v11);
          const p01 = this._project(v01);

          if (p00.depth > 0.1 && p10.depth > 0.1 && p11.depth > 0.1 && p01.depth > 0.1) {
            const zc = (p00.depth + p10.depth + p11.depth + p01.depth) / 4;
            primitives.push({
              type: 'terrain_quad',
              v00, v10, v11, v01,
              p00, p10, p11, p01,
              zc
            });
          }
        }
      }
    }

    // C. Generate Link and Flowing Pulse Primitives
    const flowSpeed = 0.22; // Speed factor of the pulses
    this.links.forEach(link => {
      const fromPt = this.points.find(p => p.id === link.from);
      const toPt = this.points.find(p => p.id === link.to);
      if (fromPt && toPt) {
        const projFrom = this._project(fromPt);
        const projTo = this._project(toPt);
        if (projFrom.depth > 0.1 && projTo.depth > 0.1) {
          primitives.push({
            type: 'link',
            from: projFrom,
            to: projTo,
            zc: (projFrom.depth + projTo.depth) / 2,
            color: link.color || '#00c0ff'
          });

          // Generate 2 flowing data pulse packets traversing each path link
          const offsets = [0, 0.5];
          offsets.forEach(offset => {
            const t = ((Date.now() * 0.001 * flowSpeed) + offset) % 1.0;
            const x = fromPt.x + (toPt.x - fromPt.x) * t;
            const y = fromPt.y + (toPt.y - fromPt.y) * t;
            const z = fromPt.z + (toPt.z - fromPt.z) * t;
            const projPulse = this._project({ x, y, z });
            if (projPulse.depth > 0.1) {
              primitives.push({
                type: 'pulse',
                proj: projPulse,
                zc: projPulse.depth,
                color: link.color || '#00f2ff',
                size: 3.5
              });
            }
          });
        }
      }
    });

    // D. Generate Point Primitives
    this.points.forEach(pt => {
      const proj = this._project(pt);
      if (proj.depth > 0.1) {
        primitives.push({
          type: 'point',
          point: pt,
          proj,
          zc: proj.depth
        });
      }
    });

    // 3. Back-to-front sorting (Painter's Algorithm)
    primitives.sort((a, b) => b.zc - a.zc);

    // 4. Render sorted primitives
    primitives.forEach(prim => {
      if (prim.type === 'grid_line') {
        const fogOpacity = this._getFogOpacity(prim.zc, prim.isRing ? 0.45 : 0.6);
        ctx.save();
        ctx.strokeStyle = prim.color;
        ctx.globalAlpha = fogOpacity;
        ctx.lineWidth = prim.isRing ? 0.75 : 0.5;
        ctx.beginPath();
        ctx.moveTo(prim.p1.u, prim.p1.v);
        ctx.lineTo(prim.p2.u, prim.p2.v);
        ctx.stroke();
        ctx.restore();
      } 
      
      else if (prim.type === 'terrain_quad') {
        ctx.save();
        
        // Shading computation using surface normal & diffuse lighting
        const ux = prim.v11.x - prim.v00.x;
        const uy = prim.v11.y - prim.v00.y;
        const uz = prim.v11.z - prim.v00.z;

        const vx = prim.v01.x - prim.v10.x;
        const vy = prim.v01.y - prim.v10.y;
        const vz = prim.v01.z - prim.v10.z;

        const nx = uy * vz - uz * vy;
        const ny = uz * vx - ux * vz;
        const nz = ux * vy - uy * vx;

        const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
        let idx = 0; let idy = 0; let idz = 1;
        if (len > 0.0001) {
          idx = nx / len;
          idy = ny / len;
          idz = nz / len;
        }

        // Lighting direction (from top-right-front)
        const lx = 0.5; const ly = 0.6; const lz = 0.9;
        const llen = Math.sqrt(lx * lx + ly * ly + lz * lz);
        const dot = idx * (lx / llen) + idy * (ly / llen) + idz * (lz / llen);
        const intensity = Math.max(0.2, 0.45 + 0.55 * dot);

        // Map height to responsive neon HSL palette
        const h = (prim.v00.z + prim.v10.z + prim.v11.z + prim.v01.z) / 4;
        const minH = -15;
        const maxH = 15;
        const ratio = Math.max(0, Math.min(1, (h - minH) / (maxH - minH)));
        
        // High height: neon pink/purple, Low height: deep space cyan/navy
        const hue = 250 - ratio * 130; // HSL 250 (Purple) to 120 (Greenish-Blue)
        const lit = Math.round(10 + intensity * 28);
        const baseColor = `hsl(${hue}, 80%, ${lit}%)`;

        const fogFactor = this._getFogOpacity(prim.zc);

        // Draw Shaded Polygon Face
        ctx.fillStyle = baseColor;
        ctx.globalAlpha = fogFactor * 0.40;
        ctx.beginPath();
        ctx.moveTo(prim.p00.u, prim.p00.v);
        ctx.lineTo(prim.p10.u, prim.p10.v);
        ctx.lineTo(prim.p11.u, prim.p11.v);
        ctx.lineTo(prim.p01.u, prim.p01.v);
        ctx.closePath();
        ctx.fill();

        // Draw Glowing Grid Wireframe on top
        ctx.strokeStyle = `hsl(${hue}, 90%, 55%)`;
        ctx.globalAlpha = fogFactor * 0.18;
        ctx.lineWidth = 0.5;
        ctx.stroke();

        ctx.restore();
      } 
      
      else if (prim.type === 'link') {
        const fogFactor = this._getFogOpacity(prim.zc);
        ctx.save();
        ctx.strokeStyle = prim.color;
        ctx.globalAlpha = fogFactor * 0.65;
        ctx.lineWidth = 1.8;
        ctx.setLineDash([4, 4]); // Futuristic data link dashed line styling
        ctx.beginPath();
        ctx.moveTo(prim.from.u, prim.from.v);
        ctx.lineTo(prim.to.u, prim.to.v);
        ctx.stroke();
        ctx.restore();
      } 
      
      else if (prim.type === 'pulse') {
        const fogFactor = this._getFogOpacity(prim.zc);
        const fov = this.camera.fov ?? 400;
        const scaledSize = Math.max(1.5, (prim.size * fov) / prim.zc);
        ctx.save();
        
        // Inner Core of pulse particle
        ctx.globalAlpha = fogFactor * 0.95;
        ctx.fillStyle = prim.color;
        ctx.beginPath();
        ctx.arc(prim.proj.u, prim.proj.v, scaledSize, 0, Math.PI * 2);
        ctx.fill();

        // Outer Glow of pulse particle
        ctx.globalAlpha = fogFactor * 0.35;
        ctx.beginPath();
        ctx.arc(prim.proj.u, prim.proj.v, scaledSize * 2.4, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
      } 
      
      else if (prim.type === 'point') {
        const pt = prim.point;
        const proj = prim.proj;
        const color = pt.color || '#00f2ff';
        const size = pt.size || 8;
        const fogFactor = this._getFogOpacity(prim.zc);

        // Distance scale for perspective size scaling
        const fov = this.camera.fov ?? 400;
        const scaledSize = Math.max(2, (size * fov) / prim.zc);

        ctx.save();

        // A. Draw Motion Trails (Velocity Faded)
        const trail = this._trails.get(pt.id);
        if (trail && trail.length > 1) {
          ctx.lineWidth = 1.5;
          for (let i = 0; i < trail.length - 1; i++) {
            const p1 = this._project(trail[i]);
            const p2 = this._project(trail[i+1]);
            if (p1.depth > 0.1 && p2.depth > 0.1) {
              const segZc = (p1.depth + p2.depth) / 2;
              const segFog = this._getFogOpacity(segZc);
              const opacity = (i / trail.length) * 0.45 * segFog;
              
              ctx.strokeStyle = color;
              ctx.globalAlpha = opacity;
              ctx.beginPath();
              ctx.moveTo(p1.u, p1.v);
              ctx.lineTo(p2.u, p2.v);
              ctx.stroke();
            }
          }
        }

        // B. Render Dual Bloom/Glow effects
        ctx.globalAlpha = fogFactor * 0.15;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(proj.u, proj.v, scaledSize * 2.6, 0, Math.PI * 2);
        ctx.fill();

        ctx.globalAlpha = fogFactor * 0.35;
        ctx.beginPath();
        ctx.arc(proj.u, proj.v, scaledSize * 1.6, 0, Math.PI * 2);
        ctx.fill();

        // C. Draw Custom / Heading Oriented Glyph
        ctx.globalAlpha = fogFactor;
        ctx.fillStyle = color;
        ctx.strokeStyle = color;
        ctx.shadowBlur = 8;
        ctx.shadowColor = color;

        // Auto-calculating screen space heading vector rotation angle
        let angle = 0;
        const hasHeading = typeof pt.heading === 'number';
        if (hasHeading) {
          const headingRad = (pt.heading! * Math.PI) / 180;
          const dx = Math.sin(headingRad);
          const dy = Math.cos(headingRad);
          const p2 = { x: pt.x + dx * 2.5, y: pt.y + dy * 2.5, z: pt.z };
          const proj2 = this._project(p2);
          angle = Math.atan2(proj2.v - proj.v, proj2.u - proj.u);
        }

        ctx.translate(proj.u, proj.v);
        if (hasHeading) {
          ctx.rotate(angle);
        }

        ctx.beginPath();
        const glyph = pt.glyph || 'circle';
        if (glyph === 'airplane' || glyph === 'aircraft' || glyph === 'arrow' || (hasHeading && glyph === 'circle')) {
          // Sleek delta wing triangle shape representing oriented travel
          const sz = scaledSize;
          ctx.moveTo(sz * 1.3, 0);
          ctx.lineTo(-sz * 0.8, -sz * 0.7);
          ctx.lineTo(-sz * 0.4, 0);
          ctx.lineTo(-sz * 0.8, sz * 0.7);
          ctx.closePath();
          ctx.fill();
          ctx.lineWidth = 1;
          ctx.strokeStyle = '#ffffff';
          ctx.stroke();
        } else if (glyph === 'triangle') {
          const sz = scaledSize;
          ctx.moveTo(0, -sz);
          ctx.lineTo(-sz * 0.8, sz * 0.8);
          ctx.lineTo(sz * 0.8, sz * 0.8);
          ctx.closePath();
          ctx.fill();
        } else if (glyph === 'diamond') {
          const sz = scaledSize;
          ctx.moveTo(0, -sz);
          ctx.lineTo(sz, 0);
          ctx.lineTo(0, sz);
          ctx.lineTo(-sz, 0);
          ctx.closePath();
          ctx.fill();
        } else if (glyph === 'square') {
          const sz = scaledSize;
          ctx.rect(-sz/2, -sz/2, sz, sz);
          ctx.fill();
        } else {
          ctx.arc(0, 0, scaledSize / 2, 0, Math.PI * 2);
          ctx.fill();
        }

        // Reset transforms so label text renders non-rotated
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const dpr = window.devicePixelRatio || 1;
        ctx.scale(dpr, dpr);
        ctx.shadowBlur = 0; // disable shadow for label rendering

        // D. Draw Info Label
        if (pt.label) {
          ctx.globalAlpha = fogFactor * 0.88;
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 9px "JetBrains Mono", "Fira Code", monospace';
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(pt.label, proj.u + scaledSize + 5, proj.v);

          // Subtitle displaying elevation coordinates
          ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
          ctx.font = '8px monospace';
          ctx.fillText(`ALT: ${Math.round(pt.z)}`, proj.u + scaledSize + 5, proj.v + 10);
        }

        ctx.restore();
      }
    });

    // 5. Draw concentric compass horizon around radar border
    this._drawHUDHorizon(ctx);
  }

  // Draw premium digital navigation compass lines and bounding indicators
  private _drawHUDHorizon(ctx: CanvasRenderingContext2D) {
    ctx.save();
    ctx.strokeStyle = 'rgba(0, 242, 255, 0.15)';
    ctx.lineWidth = 1;

    // Outer cyber-corners
    const p = 12;
    const w = this._canvasW;
    const h = this._canvasH;

    // Top-Left corner
    ctx.beginPath();
    ctx.moveTo(p, p + 15);
    ctx.lineTo(p, p);
    ctx.lineTo(p + 15, p);
    ctx.stroke();

    // Top-Right corner
    ctx.beginPath();
    ctx.moveTo(w - p, p + 15);
    ctx.lineTo(w - p, p);
    ctx.lineTo(w - p - 15, p);
    ctx.stroke();

    // Bottom-Left corner
    ctx.beginPath();
    ctx.moveTo(p, h - p - 15);
    ctx.lineTo(p, h - p);
    ctx.lineTo(p + 15, h - p);
    ctx.stroke();

    // Bottom-Right corner
    ctx.beginPath();
    ctx.moveTo(w - p, h - p - 15);
    ctx.lineTo(w - p, h - p);
    ctx.lineTo(w - p - 15, h - p);
    ctx.stroke();

    ctx.restore();
  }

  // Pointer/Mouse drag orbit listeners
  private _onPointerDown(e: PointerEvent) {
    this._isDragging = true;
    this._lastPointerX = e.clientX;
    this._lastPointerY = e.clientY;
    this._canvas.setPointerCapture(e.pointerId);
  }

  private _onPointerMove(e: PointerEvent) {
    if (!this._isDragging) return;
    const dx = e.clientX - this._lastPointerX;
    const dy = e.clientY - this._lastPointerY;
    this._lastPointerX = e.clientX;
    this._lastPointerY = e.clientY;

    const currentYaw = this.camera.yaw ?? 45;
    const currentPitch = this.camera.pitch ?? 35;

    // Update yaw and pitch based on delta dragging
    const newYaw = (currentYaw - dx * 0.45) % 360;
    const newPitch = Math.max(5, Math.min(85, currentPitch + dy * 0.45));

    this.camera = {
      ...this.camera,
      yaw: newYaw < 0 ? newYaw + 360 : newYaw,
      pitch: newPitch
    };

    // Dispatch event so parent layout views can react to manual adjustments
    this.dispatchEvent(new CustomEvent('camera-change', {
      detail: { camera: this.camera }
    }));
  }

  private _onPointerUp(e: PointerEvent) {
    this._isDragging = false;
    this._canvas.releasePointerCapture(e.pointerId);
  }

  render() {
    const yaw = Math.round(this.camera.yaw ?? 45);
    const pitch = Math.round(this.camera.pitch ?? 35);
    const zoom = (this.camera.zoom ?? 1.0).toFixed(2);

    return html`
      <div class="viewport-wrapper">
        <div class="hud-overlay">
          <div class="hud-title">
            <span class="live-pulse"></span>
            Tactical Stage 3D
          </div>
          <div class="hud-subtitle">
            Generic 2.5D Projection Engine v2.0
          </div>
        </div>

        <canvas
          @pointerdown=${this._onPointerDown}
          @pointermove=${this._onPointerMove}
          @pointerup=${this._onPointerUp}
        ></canvas>

        <div class="camera-hud">
          <div class="hud-row">
            <span>Yaw:</span>
            <span class="hud-value">${yaw}°</span>
          </div>
          <div class="hud-row">
            <span>Pitch:</span>
            <span class="hud-value">${pitch}°</span>
          </div>
          <div class="hud-row">
            <span>Zoom:</span>
            <span class="hud-value">${zoom}x</span>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'gdm-3d-scene': GdmStage3DScene;
  }
}
