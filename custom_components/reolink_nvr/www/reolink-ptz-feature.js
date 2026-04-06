/**
 * Reolink PTZ Feature — Card feature for PTZ controls.
 *
 * Attaches to any HA entity card (tile, picture-entity, etc.) and provides
 * compact PTZ directional controls + zoom.
 *
 * Usage:
 *   type: tile
 *   entity: camera.reolink_nvr_office_ch0
 *   features:
 *     - type: custom:reolink-ptz-feature
 *       show_zoom: true
 *       show_presets: true
 */

(async () => {

await customElements.whenDefined("ha-panel-lovelace");

const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

const supportsPtzFeature = (stateObj) => {
  if (!stateObj || !stateObj.entity_id) return false;
  return (
    stateObj.entity_id.startsWith("camera.") &&
    stateObj.attributes &&
    stateObj.attributes.ptz_supported === true
  );
};

class ReolinkPtzFeature extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      stateObj: { type: Object },
    };
  }

  static getConfigElement() {
    return document.createElement("reolink-ptz-feature-editor");
  }

  static getStubConfig() {
    return {
      type: "custom:reolink-ptz-feature",
      show_zoom: true,
      show_presets: false,
    };
  }

  setConfig(config) {
    this.config = {
      show_zoom: true,
      show_presets: false,
      ...config,
    };
  }

  _sendCommand(command) {
    if (!this.stateObj || !this.hass) return;

    const base = this.stateObj.entity_id.replace("camera.", "");
    const pattern = base.replace("_camera", "");
    const buttonEntity = `button.${pattern}_ptz_${command}`;

    if (this.hass.states[buttonEntity]) {
      this.hass.callService("button", "press", {
        entity_id: buttonEntity,
      });
    } else {
      this.hass.callService("reolink_nvr", "ptz_control", {
        entity_id: this.stateObj.entity_id,
        command: command,
      });
    }
  }

  _handleStart(command) {
    this._sendCommand(command);
    this._interval = setInterval(() => this._sendCommand(command), 300);
  }

  _handleEnd() {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = null;
    }
    this._sendCommand("stop");
  }

  _handlePreset(e) {
    if (!this.stateObj || !this.hass) return;
    const base = this.stateObj.entity_id.replace("camera.", "");
    const pattern = base.replace("_camera", "");
    const selectEntity = `select.${pattern}_ptz_preset`;

    this.hass.callService("select", "select_option", {
      entity_id: selectEntity,
      option: e.target.value,
    });
  }

  _getPresets() {
    if (!this.stateObj || !this.hass) return [];
    const base = this.stateObj.entity_id.replace("camera.", "");
    const pattern = base.replace("_camera", "");
    const selectEntity = `select.${pattern}_ptz_preset`;
    const state = this.hass.states[selectEntity];
    return state && state.attributes ? state.attributes.options || [] : [];
  }

  render() {
    if (
      !this.config ||
      !this.hass ||
      !this.stateObj ||
      !supportsPtzFeature(this.stateObj)
    ) {
      return html``;
    }

    const showZoom = this.config.show_zoom;
    const showPresets = this.config.show_presets;
    const presets = showPresets ? this._getPresets() : [];

    return html`
      <div class="ptz-feature">
        <div class="ptz-grid">
          <!-- Row 1: Up -->
          <div class="spacer"></div>
          <button
            class="ptz-btn"
            @pointerdown=${() => this._handleStart("up")}
            @pointerup=${this._handleEnd}
            @pointerleave=${this._handleEnd}
            title="Pan Up"
          >
            <ha-icon icon="mdi:chevron-up"></ha-icon>
          </button>
          <div class="spacer"></div>

          <!-- Row 2: Left / Home / Right -->
          <button
            class="ptz-btn"
            @pointerdown=${() => this._handleStart("left")}
            @pointerup=${this._handleEnd}
            @pointerleave=${this._handleEnd}
            title="Pan Left"
          >
            <ha-icon icon="mdi:chevron-left"></ha-icon>
          </button>
          <button
            class="ptz-btn home-btn"
            @click=${() => this._sendCommand("stop")}
            title="Stop"
          >
            <ha-icon icon="mdi:circle-outline"></ha-icon>
          </button>
          <button
            class="ptz-btn"
            @pointerdown=${() => this._handleStart("right")}
            @pointerup=${this._handleEnd}
            @pointerleave=${this._handleEnd}
            title="Pan Right"
          >
            <ha-icon icon="mdi:chevron-right"></ha-icon>
          </button>

          <!-- Row 3: Down -->
          <div class="spacer"></div>
          <button
            class="ptz-btn"
            @pointerdown=${() => this._handleStart("down")}
            @pointerup=${this._handleEnd}
            @pointerleave=${this._handleEnd}
            title="Pan Down"
          >
            <ha-icon icon="mdi:chevron-down"></ha-icon>
          </button>
          <div class="spacer"></div>
        </div>

        ${showZoom
          ? html`
              <div class="zoom-row">
                <button
                  class="ptz-btn zoom-btn"
                  @pointerdown=${() => this._handleStart("zoom_in")}
                  @pointerup=${this._handleEnd}
                  @pointerleave=${this._handleEnd}
                  title="Zoom In"
                >
                  <ha-icon icon="mdi:magnify-plus-outline"></ha-icon>
                </button>
                <button
                  class="ptz-btn zoom-btn"
                  @pointerdown=${() => this._handleStart("zoom_out")}
                  @pointerup=${this._handleEnd}
                  @pointerleave=${this._handleEnd}
                  title="Zoom Out"
                >
                  <ha-icon icon="mdi:magnify-minus-outline"></ha-icon>
                </button>
              </div>
            `
          : ""}
        ${showPresets && presets.length > 0
          ? html`
              <div class="preset-row">
                <select class="preset-select" @change=${this._handlePreset}>
                  <option value="" disabled selected>Presets...</option>
                  ${presets.map(
                    (p) => html`<option value=${p}>${p}</option>`
                  )}
                </select>
              </div>
            `
          : ""}
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }

      .ptz-feature {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
      }

      .ptz-grid {
        display: grid;
        grid-template-columns: var(--feature-height, 42px) var(--feature-height, 42px) var(--feature-height, 42px);
        grid-template-rows: var(--feature-height, 42px) var(--feature-height, 42px) var(--feature-height, 42px);
        gap: var(--feature-button-spacing, 4px);
      }

      .ptz-btn {
        width: var(--feature-height, 42px);
        height: var(--feature-height, 42px);
        border-radius: var(--feature-border-radius, 12px);
        border: none;
        background: var(--feature-color, rgba(var(--rgb-primary-text-color), 0.05));
        color: var(--primary-text-color);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.15s;
        -webkit-tap-highlight-color: transparent;
        touch-action: none;
      }

      .ptz-btn:hover {
        background: rgba(var(--rgb-primary-text-color), 0.1);
      }

      .ptz-btn:active {
        background: rgba(var(--rgb-primary-text-color), 0.15);
      }

      .home-btn {
        background: rgba(var(--rgb-primary-text-color), 0.03);
      }

      .spacer {
        width: var(--feature-height, 42px);
        height: var(--feature-height, 42px);
      }

      .zoom-row {
        display: flex;
        gap: var(--feature-button-spacing, 4px);
      }

      .zoom-btn {
        width: 64px;
      }

      .preset-row {
        width: 100%;
        padding: 0 8px;
        box-sizing: border-box;
      }

      .preset-select {
        width: 100%;
        height: var(--feature-height, 42px);
        border-radius: var(--feature-border-radius, 12px);
        border: 1px solid rgba(var(--rgb-primary-text-color), 0.1);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 13px;
        padding: 0 12px;
        cursor: pointer;
      }
    `;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._interval) {
      clearInterval(this._interval);
    }
  }
}

customElements.define("reolink-ptz-feature", ReolinkPtzFeature);

class ReolinkPtzFeatureEditor extends LitElement {
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
        name: "show_zoom",
        selector: { boolean: {} },
      },
      {
        name: "show_presets",
        selector: { boolean: {} },
      },
    ];
  }

  render() {
    if (!this.hass || !this._config) return html``;

    const data = {
      show_zoom: this._config.show_zoom !== false,
      show_presets: this._config.show_presets || false,
    };

    return html`
      <ha-form
        .hass=${this.hass}
        .data=${data}
        .schema=${this._schema}
        .computeLabel=${(s) => {
          const labels = {
            show_zoom: "Show Zoom Controls",
            show_presets: "Show Preset Selector",
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

customElements.define("reolink-ptz-feature-editor", ReolinkPtzFeatureEditor);

window.customCardFeatures = window.customCardFeatures || [];
window.customCardFeatures.push({
  type: "reolink-ptz-feature",
  name: "Reolink PTZ Controls",
  supported: supportsPtzFeature,
  configurable: true,
});

})();
