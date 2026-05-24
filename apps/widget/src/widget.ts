// PartsAI embeddable widget
// Loaded as: <script src="https://widget.partsai.com/widget.js" data-key="pk_live_..."></script>
//
// At Phase 1 this is a placeholder. Real implementation lands in Week 2 step 10.

interface WidgetConfig {
  apiKey: string;
  apiUrl: string;
  module: 'parts_id' | 'technician' | 'order';
  language: string;
}

function readConfigFromScriptTag(): WidgetConfig | null {
  const script = document.currentScript as HTMLScriptElement | null;
  if (!script) return null;
  const apiKey = script.dataset.key;
  if (!apiKey) {
    console.error('[PartsAI] widget script missing data-key attribute');
    return null;
  }
  return {
    apiKey,
    apiUrl: script.dataset.api ?? 'https://api.partsai.com',
    module: (script.dataset.module as WidgetConfig['module']) ?? 'parts_id',
    language: script.dataset.language ?? 'en',
  };
}

function mount(config: WidgetConfig): void {
  const root = document.createElement('div');
  root.id = 'partsai-widget-root';
  root.dataset.module = config.module;
  document.body.appendChild(root);
  // TODO Week 2: floating button, chat panel, message stream, product cards.
  console.log('[PartsAI] widget placeholder mounted', config);
}

const config = readConfigFromScriptTag();
if (config) mount(config);
