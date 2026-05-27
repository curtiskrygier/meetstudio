import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-table-view')
export class GdmStageTableView extends LitElement {
  @property({ type: Array }) headers: string[] = [];
  @property({ type: Array }) rows: any[][] = []; // supports standard strings/numbers or formatted objects
  @property({ type: String }) accentColor = 'accent';

  static styles = css`
    :host {
      display: block;
      width: 100%;
      overflow-x: auto;
      box-sizing: border-box;
    }
    
    /* Scrollbar */
    :host::-webkit-scrollbar {
      height: 4px;
    }
    :host::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.01);
    }
    :host::-webkit-scrollbar-thumb {
      background: rgba(0, 242, 255, 0.15);
      border-radius: 2px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-family: 'Google Sans', 'Inter', system-ui, sans-serif;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.85);
    }

    thead {
      border-bottom: 2px solid var(--table-accent-semi, rgba(0, 242, 255, 0.15));
    }

    th {
      padding: 10px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--table-accent, #00f2ff);
      opacity: 0.85;
      white-space: nowrap;
    }

    tbody tr {
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      transition: background-color 0.2s ease;
    }

    tbody tr:hover {
      background-color: rgba(255, 255, 255, 0.02);
    }

    td {
      padding: 12px 12px;
      vertical-align: middle;
      white-space: nowrap;
    }

    /* Column Alignment helpers */
    .align-right {
      text-align: right;
    }
    .align-center {
      text-align: center;
    }

    /* Monospace formatting for numbers & statuses */
    .mono-cell {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 500;
    }

    /* Custom sub-text support */
    .subtext {
      display: block;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.4);
      margin-top: 2px;
    }
  `;

  private _resolveColor(colorName: string): string {
    if (!colorName) return 'inherit';
    if (colorName === 'accent' || colorName === 'cyan') return '#00f2ff';
    if (colorName === 'success') return '#00ff88';
    if (colorName === 'warning') return '#ffd60a';
    if (colorName === 'danger') return '#ff3b57';
    if (colorName === 'mute') return 'rgba(255,255,255,0.45)';
    return colorName;
  }

  private _renderCell(cell: any) {
    if (cell === null || cell === undefined) return '';

    // If cell is a simple string or number
    if (typeof cell !== 'object') {
      const isNum = typeof cell === 'number' || (!isNaN(Number(cell)) && !isNaN(parseFloat(cell)));
      return html`
        <span class="${isNum ? 'mono-cell' : ''}">${cell}</span>
      `;
    }

    // If cell is a formatted cell object: { text, subtext, color, mono, uppercase, align }
    const cellColor = this._resolveColor(cell.color || '');
    const isMono = cell.mono === true || cell.mono === 'true';
    const isUppercase = cell.uppercase === true || cell.uppercase === 'true';

    const cellStyle = cellColor !== 'inherit' ? `color: ${cellColor};` : '';
    const classes = [
      isMono ? 'mono-cell' : '',
      isUppercase ? 'uppercase' : ''
    ].filter(Boolean).join(' ');

    return html`
      <span class="${classes}" style="${cellStyle}">
        ${cell.text}
        ${cell.subtext ? html`<span class="subtext">${cell.subtext}</span>` : ''}
      </span>
    `;
  }

  render() {
    let resolvedAccent = this.accentColor;
    if (this.accentColor === 'accent' || this.accentColor === 'cyan') resolvedAccent = '#00f2ff';
    else if (this.accentColor === 'success') resolvedAccent = '#00ff88';
    else if (this.accentColor === 'warning') resolvedAccent = '#ffd60a';
    else if (this.accentColor === 'danger') resolvedAccent = '#ff3b57';

    // Parse inputs if they come in as stringified JSON representation from client/server
    let resolvedHeaders = this.headers;
    let resolvedRows = this.rows;

    try {
      if (typeof resolvedHeaders === 'string') {
        resolvedHeaders = JSON.parse(resolvedHeaders);
      }
    } catch (_) {}

    try {
      if (typeof resolvedRows === 'string') {
        resolvedRows = JSON.parse(resolvedRows);
      }
    } catch (_) {}

    if (!Array.isArray(resolvedHeaders)) resolvedHeaders = [];
    if (!Array.isArray(resolvedRows)) resolvedRows = [];

    return html`
      <div style="--table-accent: ${resolvedAccent}; --table-accent-semi: ${resolvedAccent}26;">
        <table>
          <thead>
            <tr>
              ${resolvedHeaders.map((hdr, idx) => {
                // If the first column is aligned left, others right-aligned if they contain numbers
                const isFirst = idx === 0;
                return html`
                  <th class="${isFirst ? '' : 'align-right'}">${hdr}</th>
                `;
              })}
            </tr>
          </thead>
          <tbody>
            ${resolvedRows.map(row => html`
              <tr>
                ${(Array.isArray(row) ? row : []).map((cell, idx) => {
                  const isFirst = idx === 0;
                  const cellObjAlign = cell && typeof cell === 'object' && cell.align;
                  let alignClass = isFirst ? '' : 'align-right';
                  if (cellObjAlign === 'left') alignClass = '';
                  else if (cellObjAlign === 'center') alignClass = 'align-center';
                  else if (cellObjAlign === 'right') alignClass = 'align-right';

                  return html`
                    <td class="${alignClass}">
                      ${this._renderCell(cell)}
                    </td>
                  `;
                })}
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }
}
