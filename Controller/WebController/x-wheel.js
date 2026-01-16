const template = document.createElement('template');
template.innerHTML = `
<svg width="100%" height="100%" viewBox="0 0 200 200" style="cursor: grab;">
  <g id="wheel-group">
    <circle cx="100" cy="100" r="90" fill="none" stroke="black" stroke-width="10"></circle>
    <circle cx="100" cy="100" r="5" fill="gray"></circle>
    <line x1="100" y1="20" x2="100" y2="100" stroke="grey" stroke-width="5"></line>
  </g>
</svg>
`;

/**
 * A custom web component that renders a rotatable wheel SVG.
 * 
 * Usage:
 * - Add to HTML: <wheel min="-90" max="90" step="45"></wheel>
 * - Listen for 'rotate' events: element.addEventListener('rotate', (e) => console.log(e.detail.angle));
 * - Set rotation programmatically: element.setRotation(45);
 * - Configure min/max/step via attributes or JavaScript properties.
 */
class XWheel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' }).append(template.content.cloneNode(true));
    this.wheelGroup = this.shadowRoot.querySelector('#wheel-group');
    this.rotation = 0;
    this.isDragging = false;
    this.startAngle = 0;
    this._min = -Infinity;
    this._max = Infinity;
    this._step = 1;
    this._default = 0;
    this._returnToDefault = false;
  }

  static get observedAttributes() {
    return ['default', 'min', 'max', 'step', 'return-to-default'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    switch (name) {
      case 'return-to-default':
        this._returnToDefault = newValue !== null;
        break;
      case 'default':
        const defaultVal = parseFloat(newValue);
        this._default = isNaN(defaultVal) ? 0 : defaultVal;
        this.setRotation(this._default, false);
        break;
      case 'min':
        const minVal = parseFloat(newValue);
        this._min = isNaN(minVal) ? -Infinity : minVal;
        this.clampRotation();
        this.updateRotation();
        break;
      case 'max':
        const maxVal = parseFloat(newValue);
        this._max = isNaN(maxVal) ? Infinity : maxVal;
        this.clampRotation();
        this.updateRotation();
        break;
      case 'step':
        this._step = parseFloat(newValue) || 1;
        this.snapRotation();
        this.updateRotation();
        break;
    }
  }

  get default() {
    return this._default;
  }

  set default(value) {
    const valueFloat = parseFloat(value);
    const defaultValue = isNaN(valueFloat) ? 0 : valueFloat;
    this.setAttribute('default', defaultValue);
  }

  get min() {
    return this._min;
  }

  set min(value) {
    const valueFloat = parseFloat(value);
    const minValue = isNaN(valueFloat) ? -Infinity : valueFloat;
    this.setAttribute('min', minValue);
  }

  get max() {
    return this._max;
  }

  set max(value) {
    const valueFloat = parseFloat(value);
    const maxValue = isNaN(valueFloat) ? Infinity : valueFloat;
    this.setAttribute('max', maxValue);
  }

  get step() {
    return this._step;
  }

  set step(value) {
    const valueFloat = parseFloat(value);
    const stepValue = isNaN(valueFloat) || valueFloat === 0 ? 1 : valueFloat;
    this.setAttribute('step', stepValue);
  }

  connectedCallback() {
    this.addEventListeners();
  }

  addEventListeners() {
    const svg = this.shadowRoot.querySelector('svg');
    svg.addEventListener('pointerdown', this.startDrag.bind(this));
    svg.addEventListener('pointermove', this.drag.bind(this));
    svg.addEventListener('pointerup', this.endDrag.bind(this));
  }

  startDrag(event/*: PointerEvent */) {
    this.isDragging = true;
    const rect = this.shadowRoot.querySelector('svg').getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    this.startAngle = Math.atan2(event.clientY - centerY, event.clientX - centerX) * (180 / Math.PI);
    event.preventDefault();
  }

  drag(event/*: PointerEvent */) {
    if (!this.isDragging) return;
    
    // Prevent default to avoid scrolling/selection while dragging
    event.preventDefault();

    const rect = this.shadowRoot.querySelector('svg').getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Calculate current angle in degrees [-180, 180]
    const currentAngle = Math.atan2(event.clientY - centerY, event.clientX - centerX) * (180 / Math.PI);
    
    // Calculate the raw difference
    let delta = currentAngle - this.startAngle;

    // Normalize delta to [-180, 180] to handle the wrap-around case.
    // Ideally, a single frame movement shouldn't exceed 180 degrees.
    // If delta > 180, it means we crossed the boundary counter-clockwise (e.g., -179 to 179).
    // If delta < -180, we crossed clockwise (e.g., 179 to -179).
    if (delta > 180) {
      delta -= 360;
    } else if (delta < -180) {
      delta += 360;
    }

    // Calculate potential new rotation
    let newRotation = this.rotation + delta;

    // Apply constraints
    newRotation = this.snapToStep(newRotation);
    newRotation = Math.max(this._min, Math.min(this._max, newRotation));

    // Update if changed
    if (newRotation !== this.rotation) {
      this.rotation = newRotation;
      // Update startAngle to currentAngle to keep subsequent deltas relative to the new position
      this.startAngle = currentAngle;
      
      this.updateRotation();
      this.dispatchEvent(new CustomEvent('rotate', { detail: { angle: this.rotation } }));
    }
  }

  endDrag() {
    this.isDragging = false;

    // Return to default position if enabled.
    if (this._returnToDefault) {
      this.setRotation(this._default, true);
    }
  }

  updateRotation() {
    this.wheelGroup.setAttribute('transform', `rotate(${this.rotation} 100 100)`);
  }

  clampRotation() {
    this.rotation = Math.max(this._min, Math.min(this._max, this.rotation));
  }

  snapToStep(value) {
    return Math.round(value / this._step) * this._step;
  }

  snapRotation() {
    this.rotation = this.snapToStep(this.rotation);
  }

  setRotation(angle/*: number*/, publishEvent/*: boolean*/ = true) {
    this.rotation = this.snapToStep(angle);
    this.clampRotation();
    this.updateRotation();
    if (publishEvent) {
      this.dispatchEvent(new CustomEvent('rotate', { detail: { angle: this.rotation } }));
    }
  }
}

customElements.define('x-wheel', XWheel);