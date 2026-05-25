export interface A2UIComponent {
  id: string;
  element: string;
  props: Record<string, any>;
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
  private onRender: A2UIRenderCallback;

  constructor(onRender: A2UIRenderCallback) {
    this.onRender = onRender;
  }

  /**
   * Process an incoming WebSocket message.
   * Returns true if the message was an A2UI protocol message and was consumed.
   */
  handleMessage(msg: any): boolean {
    if (msg.type === 'surfaceUpdate') {
      if (msg.surfaceUpdate?.components) {
        for (const comp of msg.surfaceUpdate.components) {
          this.componentBuffer.set(comp.id, comp);
        }
      }
      return true;
    }

    if (msg.type === 'dataModelUpdate') {
      if (msg.dataModelUpdate) {
        const dmu = msg.dataModelUpdate;
        const baseMap = this.parseDataModelContents(dmu.contents || []);
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

    if (msg.type === 'beginRendering') {
      if (msg.beginRendering?.root) {
        this.onRender(this.compile(msg.beginRendering.root));
      }
      return true;
    }

    if (msg.type === 'deleteSurface') {
      this.clear();
      this.onRender([]);
      return true;
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

  private parseDataModelContents(contents: any[]): Record<string, any> {
    const result: Record<string, any> = {};
    for (const entry of contents) {
      if (!entry || !entry.key) continue;
      if ('valueString' in entry) result[entry.key] = entry.valueString;
      else if ('valueBoolean' in entry) result[entry.key] = entry.valueBoolean;
      else if ('valueNumber' in entry) result[entry.key] = entry.valueNumber;
      else if ('valueMap' in entry) result[entry.key] = this.parseDataModelContents(entry.valueMap);
    }
    return result;
  }

  private compile(rootId: string): A2UIComponent[] {
    const out: A2UIComponent[] = [];
    const visited = new Set<string>();

    const traverse = (id: string) => {
      if (visited.has(id)) return;
      visited.add(id);

      const item = this.componentBuffer.get(id);
      if (!item?.component) return;

      const keys = Object.keys(item.component);
      if (keys.length === 0) return;
      const elementName = keys[0];
      const rawProps = item.component[elementName];

      const resolvedProps: Record<string, any> = {};
      for (const [k, v] of Object.entries(rawProps)) {
        resolvedProps[k] = this.resolveBoundValue(v);
      }

      let el = elementName.toLowerCase();
      if (!el.startsWith('gdm-') && el !== 'div') {
        if (el === 'column' || el === 'row') el = 'div';
      }

      out.push({ id: item.id, element: el, props: resolvedProps });

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
      'gdm-poll-overlay',
      'gdm-chat-card',
      'gdm-captions',
      'gdm-emoji-burst',
      'gdm-draw-overlay',
      'gdm-pointer'
    ]);

    for (const [id, item] of this.componentBuffer.entries()) {
      if (visited.has(id)) continue;
      if (!item?.component) continue;
      const keys = Object.keys(item.component);
      if (keys.length === 0) continue;
      const el = keys[0].toLowerCase();
      if (overlayTypes.has(el)) {
        traverse(id);
      }
    }

    return out;
  }
}
