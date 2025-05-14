(function() {
  const STATIC_URL = '/static/';

  // ——— Storage helpers ———
  function save(key, value) {
    try { localStorage.setItem(key, value); } catch(e){}
  }
  function load(key, fallback = null) {
    try { return localStorage.getItem(key) ?? fallback; } catch(e){ return fallback; }
  }

  // ——— Apply on load ———
  document.addEventListener('DOMContentLoaded', () => {
    // 1) Direction (default rtl)
    let dir = load('themeDir', 'rtl');
    applyDirection(dir);

    // 2) Mode (default light)
    let mode = load('themeMode', 'light');
    applyMode(mode);

    // 3) Color (default #0da487)
    let color = load('themeColor', '#0da487');
    applyColor(color);
    document.getElementById('colorPick').value = color;
  });

  // ——— Apply helpers ———
  function applyDirection(dir) {
    const html = document.documentElement;
    const body = document.body;
    const rtlLink = document.getElementById('rtl-link');
    if (dir === 'rtl') {
      html.setAttribute('dir', 'rtl');
      body.classList.add('rtl');
      body.classList.remove('ltr');
      rtlLink.href = STATIC_URL + 'css/vendors/bootstrap.rtl.css';
    } else {
      html.setAttribute('dir', 'ltr');
      body.classList.add('ltr');
      body.classList.remove('rtl');
      rtlLink.href = STATIC_URL + 'css/vendors/bootstrap.css';
    }
    save('themeDir', dir);
  }

  function applyMode(mode) {
    const body = document.body;
    const cssLink = document.getElementById('color-link');
    const darkBtn = document.getElementById('darkButton');
    const lightBtn = document.getElementById('lightButton');

    body.classList.remove('light','dark');
    body.classList.add(mode);
    cssLink.href = STATIC_URL + (mode === 'dark' ? 'css/dark.css' : 'css/style.css');

    darkBtn.classList.toggle('active', mode === 'dark');
    lightBtn.classList.toggle('active', mode === 'light');

    save('themeMode', mode);
  }

  function applyColor(color) {
    document.documentElement.style.setProperty('--theme-color', color);
  }

  // ——— Event listeners ———

  // Color picker: on change (after OK)
  document.getElementById('colorPick').addEventListener('change', function() {
    const c = this.value;
    applyColor(c);
    save('themeColor', c);
  });

  // Dark / Light
  document.getElementById('darkButton').addEventListener('click', () => applyMode('dark'));
  document.getElementById('lightButton').addEventListener('click', () => applyMode('light'));

  // RTL / LTR
  document.querySelector('.theme-setting-button.rtl').addEventListener('click', e => {
    if (e.target.classList.contains('rtl-unline')) applyDirection('ltr');
    if (e.target.classList.contains('rtl-outline')) applyDirection('rtl');
  });

})();
