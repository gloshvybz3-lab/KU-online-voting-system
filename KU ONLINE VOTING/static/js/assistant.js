(() => {
  const launcher = document.getElementById('assistantLauncher');
  const panel = document.getElementById('assistantPanel');
  const close = document.getElementById('assistantClose');
  const form = document.getElementById('assistantForm');
  const input = document.getElementById('assistantInput');
  const messages = document.getElementById('assistantMessages');
  if (!launcher || !panel || !form) return;

  const addMessage = (text, type, links=[]) => {
    const el = document.createElement('div');
    el.className = `assistant-message ${type}`;
    el.textContent = text;
    links.forEach(link => {
      const a = document.createElement('a');
      a.className = 'assistant-link d-block';
      a.href = link.url;
      a.textContent = `Open ${link.label}`;
      el.appendChild(a);
    });
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  };

  launcher.addEventListener('click', () => { panel.classList.toggle('d-none'); if (!panel.classList.contains('d-none')) input.focus(); });
  close?.addEventListener('click', () => panel.classList.add('d-none'));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    addMessage(value, 'user');
    input.value = '';
    try {
      const res = await fetch('/api/v1/assistant/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({message: value})
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Assistant unavailable');
      addMessage(data.message, 'bot', data.links || []);
    } catch (err) {
      addMessage('I could not process that request right now. Please use the navigation menu or try again.', 'bot');
    }
  });
})();
