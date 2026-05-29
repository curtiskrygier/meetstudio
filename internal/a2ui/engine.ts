export interface A2UIComponent {
  id: string;
  element: string;
  props: Record<string, any>;
  // True when this component was in the LATEST surfaceUpdate (vs pulled from the
  // buffer during compile). main_stage uses this to skip re-applying props for
  // buffered components, which preserves local interactive state (camera zoom,
  // toggle buttons, etc.) across server-driven partial updates.
  _fresh?: boolean;
}

export type A2UIRenderCallback = (components: A2UIComponent[]) => void;

/**
 * Official Google A2UI v0.8 spec-compliant interpreter engine.
 * Framework-agnostic — no Lit/DOM dependency. Shared between the
 * side panel (index.tsx) and the main stage (future Vite entry).
 */
export class A2UIEngine {
  private componentBuffer = new Map<string, any>();
  private dataModelStore = new Map<string, any>();
  // Component ids included in the LATEST surfaceUpdate. Used during compile() to
  // mark which components are server-fresh vs pulled from the buffer — so the
  // renderer can preserve local interactive state on buffered components.
  private _lastUpdatedIds = new Set<string>();
  private onRender: A2UIRenderCallback;

  constructor(onRender: A2UIRenderCallback) {
    this.onRender = onRender;
  }

  /**
   * Process an incoming WebSocket message.
   * Returns true if the message was an A2UI protocol message and was consumed.
   */
  handleMessage(msg: any): boolean {
    if (!msg || typeof msg !== 'object') return false;
    const msgType = Object.keys(msg)[0];
    if (!msgType) return false;

    switch (msgType) {
      case 'updateComponents': {
        const payload = msg.updateComponents;
        if (payload?.components) {
          this._lastUpdatedIds = new Set<string>();
          for (const comp of payload.components) {
            this.componentBuffer.set(comp.id, comp);
            this._lastUpdatedIds.add(comp.id);
          }
        }
        return true;
      }

      case 'updateDataModel': {
        const dmu = msg.updateDataModel;
        if (dmu) {
          const baseMap = this.parseDataModelContents(dmu.contents);
          if (dmu.path) {
            this.updateDataModelPath(dmu.path, baseMap);
          } else {
            for (const [k, v] of Object.entries(baseMap)) {
              this.dataModelStore.set(k, v);
            }
          }
        }
        return true;
      }

      case 'createSurface': {
        const payload = msg.createSurface;
        if (payload) {
          if (payload.catalogId) {
            console.warn(`[A2UI Engine] createSurface catalogId: ${payload.catalogId}`);
          }
          if (payload.root) {
            this.onRender(this.compile(payload.root));
          }
        }
        return true;
      }

      case 'deleteSurface': {
        this.clear();
        this.onRender([]);
        return true;
      }
    }

    return false;
  }

  clear() {
    this.componentBuffer.clear();
    this.dataModelStore.clear();
  }

  private resolveBoundValue(val: any): any {
    if (!val || typeof val !== 'object') return val;

    if ('literalString' in val) {
      if ('path' in val && val.path) this.updateDataModelPath(val.path, val.literalString);
      return val.literalString;
    }
    if ('literalBoolean' in val) {
      if ('path' in val && val.path) this.updateDataModelPath(val.path, val.literalBoolean);
      return val.literalBoolean;
    }
    if ('literalNumber' in val) {
      if ('path' in val && val.path) this.updateDataModelPath(val.path, val.literalNumber);
      return val.literalNumber;
    }
    if ('literalArray' in val) {
      if ('path' in val && val.path) this.updateDataModelPath(val.path, val.literalArray);
      return val.literalArray;
    }

    if ('path' in val && val.path) return this.getDataModelPath(val.path);
    return val;
  }

  private getDataModelPath(path: string): any {
    if (!path) return undefined;
    const parts = path.split('/').filter(p => p);
    let current: any = this.dataModelStore;
    for (const part of parts) {
      if (current instanceof Map) {
        current = current.get(part);
      } else if (current && typeof current === 'object') {
        current = current[part];
      } else {
        return undefined;
      }
    }
    return current;
  }

  private updateDataModelPath(path: string, val: any) {
    if (!path) return;
    const parts = path.split('/').filter(p => p);
    let current: any = this.dataModelStore;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (current instanceof Map) {
        if (!current.has(part)) current.set(part, new Map());
        current = current.get(part);
      } else {
        if (!current[part] || typeof current[part] !== 'object') current[part] = {};
        current = current[part];
      }
    }
    const lastPart = parts[parts.length - 1];
    if (current instanceof Map) {
      current.set(lastPart, val);
    } else if (current && typeof current === 'object') {
      current[lastPart] = val;
    }
  }

  private parseDataModelContents(contents: any): Record<string, any> {
    return contents && typeof contents === 'object' ? { ...contents } : {};
  }

  private compile(rootId: string): A2UIComponent[] {
    const out: A2UIComponent[] = [];
    const visited = new Set<string>();

    const traverse = (id: string) => {
      if (visited.has(id)) return;
      visited.add(id);

      const item = this.componentBuffer.get(id);
      if (!item || typeof item.component !== 'string') return;

      const elementName = item.component;
      const { id: _, component: __, ...rawProps } = item;

      const resolvedProps: Record<string, any> = {};
      for (const [k, v] of Object.entries(rawProps)) {
        resolvedProps[k] = this.resolveBoundValue(v);
      }

      let el = elementName.toLowerCase();
      if (!el.startsWith('gdm-') && el !== 'div') {
        if (el === 'column' || el === 'row') el = 'div';
      }

      out.push({
        id: item.id,
        element: el,
        props: resolvedProps,
        _fresh: this._lastUpdatedIds.has(item.id),
      });

      if (rawProps.children?.explicitList) {
        for (const childId of rawProps.children.explicitList) traverse(childId);
      } else if (rawProps.child) {
        traverse(rawProps.child);
      }
    };

    // 1. Compile the main root element tree
    traverse(rootId);

    // 2. Automatically discover and compile any active top-level overlay components
    const overlayTypes = new Set([
      'gdm-ticker',
      'gdm-chyron',
      'gdm-standby-slate',
      'gdm-poll-overlay',
      'gdm-chat-card',
      'gdm-captions',
      'gdm-emoji-burst',
      'gdm-draw-overlay',
      'gdm-pointer',
      'gdm-laser-sweep',
      'gdm-diagram-view',
      'gdm-html-panel',
      'gdm-market-ticker',
    ]);

    for (const [id, item] of this.componentBuffer.entries()) {
      if (visited.has(id)) continue;
      if (!item || typeof item.component !== 'string') continue;
      const el = item.component.toLowerCase();
      if (overlayTypes.has(el)) {
        traverse(id);
      }
    }

    return out;
  }
}
