/**
 * Reolink Camera Grid Card — Multi-camera NVR overview.
 *
 * Features:
 * - Grid of all cameras from one or more Reolink NVR instances
 * - Each cell: live stream thumbnail + name + motion badge
 * - Tap cell to open fullscreen reolink-camera-card
 * - Responsive columns (auto or configurable)
 */

// Register card synchronously so the card picker sees it immediately
window.customCards = window.customCards || [];
window.customCards.push({
  type: "reolink-camera-grid-card",
  name: "Reolink Camera Grid",
  preview: false,
  description:
    "Multi-camera grid overview for Reolink NVR. Tap a camera to expand with full PTZ and audio controls.",
});

(async () => {

await customElements.whenDefined("ha-panel-lovelace");

const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

class ReolinkCameraGridCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _expandedCamera: { type: String },
    };
  }

  constructor() {
    super();
    this._expandedCamera = null;
  }

  static getConfigElement() {
    return document.createElement("reolink-camera-grid-card-editor");
  }

  static getStubConfig(hass) {
    return {
      columns: 0, // 0 = auto
      show_motion_indicator: true,
    };
  }

  setConfig(config) {
    this.config = {
      columns: 0,
      show_motion_indicator: true,
      cameras: [],
      ...config,
    };
  }

  getCardSize() {
    const cameras = this._getCameras();
    const cols = this._getColumns();
    const rows = Math.ceil(cameras.length / cols);
    return rows * 3;
  }

  _getCameras() {
    if (!this.hass) return [];

    // If specific cameras listed in config, use those
    if (this.config.cameras && this.config.cameras.length > 0) {
      return this.config.cameras.filter((e) => this.hass.states[e]);
    }

    // Auto-discover all reolink_nvr cameras
    return Object.keys(this.hass.states).filter(
      (entityId) =>
        entityId.startsWith("camera.") &&
        (entityId.includes("reolink_nvr") ||
          (this.hass.states[entityId].attributes &&
            this.hass.states[entityId].attributes.channel !== undefined &&
            this.hass.states[entityId].attributes.stream_quality !== undefined))
    );
  }

  _getColumns() {
    if (this.config.columns > 0) return this.config.columns;
    const count = this._getCameras().length;
    if (count <= 2) return count;
    if (count <= 4) return 2;
    if (count <= 9) return 3;
    return 4;
  }

  _isMotionDetected(cameraEntityId) {
    if (!this.config.show_motion_indicator || !this.hass) return false;
    const base = cameraEntityId.replace("camera.", "");
    const pattern = base.replace("_camera", "");
    for (const [entityId, entityState] of Object.entries(this.hass.states)) {
      if (
        entityId.startsWith("binary_sensor.") &&
        entityId.includes(pattern) &&
        entityId.endsWith("_motion")
      ) {
        return entityState.state === "on";
      }
    }
    return false;
  }

  _getCameraName(entityId) {
    const state = this.hass.states[entityId];
    return state
      ? state.attributes.friendly_name || entityId
      : entityId;
  }

  _handleCameraClick(entityId) {
    this._expandedCamera = entityId;
  }

  _handleCloseExpanded() {
    this._expandedCamera = null;
  }

  render() {
    if (!this.hass || !this.config) {
      return html`<ha-card>Loading...</ha-card>`;
    }

    const cameras = this._getCameras();
    if (cameras.length === 0) {
      return html`<ha-card>
        <div class="empty">No Reolink NVR cameras found</div>
      </ha-card>`;
    }

    // Expanded view: show single camera card
    if (this._expandedCamera) {
      return html`
        <ha-card>
          <div class="expanded-view">
            <div class="expanded-header">
              <button class="back-btn" @click=${this._handleCloseExpanded}>
                <ha-icon icon="mdi:arrow-left"></ha-icon>
                <span>Back to grid</span>
              </button>
            </div>
            <reolink-camera-card
              .hass=${this.hass}
              .config=${{
                entity: this._expandedCamera,
                ptz: true,
                show_motion_indicator: true,
                show_microphone: true,
              }}
            ></reolink-camera-card>
          </div>
        </ha-card>
      `;
    }

    // Grid view
    const cols = this._getColumns();

    return html`
      <ha-card>
        <div class="grid" style="grid-template-columns: repeat(${cols}, 1fr);">
          ${cameras.map(
            (entityId) => html`
              <div
                class="grid-cell ${this._isMotionDetected(entityId)
                  ? "motion"
                  : ""}"
                @click=${() => this._handleCameraClick(entityId)}
              >
                <div class="cell-video">
                  <ha-camera-stream
                    .hass=${this.hass}
                    .stateObj=${this.hass.states[entityId]}
                    muted
                  ></ha-camera-stream>
                </div>
                <div class="cell-footer">
                  <span class="cell-name"
                    >${this._getCameraName(entityId)}</span
                  >
                  ${this._isMotionDetected(entityId)
                    ? html`<span class="cell-motion-badge">Motion</span>`
                    : ""}
                </div>
              </div>
            `
          )}
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }

      ha-card {
        overflow: hidden;
      }

      .grid {
        display: grid;
        gap: 4px;
        padding: 4px;
      }

      .grid-cell {
        position: relative;
        border-radius: 8px;
        overflow: hidden;
        background: #000;
        cursor: pointer;
        transition: transform 0.15s, box-shadow 0.15s;
      }

      .grid-cell:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }

      .grid-cell:active {
        transform: scale(0.98);
      }

      .grid-cell.motion {
        box-shadow: 0 0 0 2px rgba(244, 67, 54, 0.8);
      }

      .cell-video {
        aspect-ratio: 16 / 9;
        overflow: hidden;
      }

      .cell-video ha-camera-stream {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .cell-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 10px;
        background: var(--card-background-color, #1c1c1c);
      }

      .cell-name {
        font-size: 12px;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .cell-motion-badge {
        font-size: 10px;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 8px;
        background: rgba(244, 67, 54, 0.9);
        color: #fff;
        text-transform: uppercase;
        animation: pulse 1.5s ease-in-out infinite;
        flex-shrink: 0;
      }

      @keyframes pulse {
        0%,
        100% {
          opacity: 1;
        }
        50% {
          opacity: 0.5;
        }
      }

      /* Expanded view */
      .expanded-view {
        display: flex;
        flex-direction: column;
      }

      .expanded-header {
        padding: 8px 12px;
        background: var(--card-background-color);
      }

      .back-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        border: none;
        background: none;
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 14px;
        padding: 6px 8px;
        border-radius: 8px;
        -webkit-tap-highlight-color: transparent;
      }

      .back-btn:hover {
        background: var(--secondary-background-color);
      }

      .empty {
        padding: 24px;
        text-align: center;
        color: var(--secondary-text-color);
      }
    `;
  }
}

customElements.define("reolink-camera-grid-card", ReolinkCameraGridCard);

class ReolinkCameraGridCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
    };
  }

  setConfig(config) {
    this._config = config;
  }

  get _schema() {
    return [
      {
        name: "columns",
        selector: {
          number: { min: 0, max: 6, mode: "box" },
        },
      },
      {
        name: "show_motion_indicator",
        selector: { boolean: {} },
      },
      {
        name: "cameras",
        selector: {
          entity: { domain: "camera", multiple: true },
        },
      },
    ];
  }

  render() {
    if (!this.hass || !this._config) return html``;

    const data = {
      columns: this._config.columns || 0,
      show_motion_indicator: this._config.show_motion_indicator !== false,
      cameras: this._config.cameras || [],
    };

    return html`
      <ha-form
        .hass=${this.hass}
        .data=${data}
        .schema=${this._schema}
        .computeLabel=${(s) => {
          const labels = {
            columns: "Columns (0 = auto)",
            show_motion_indicator: "Show Motion Indicator",
            cameras: "Cameras (empty = auto-discover)",
          };
          return labels[s.name] || s.name;
        }}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `;
  }

  _valueChanged(ev) {
    const config = { ...this._config, ...ev.detail.value };
    this._config = config;
    const event = new CustomEvent("config-changed", {
      detail: { config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("reolink-camera-grid-card-editor", ReolinkCameraGridCardEditor);

})();
