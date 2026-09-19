import { renderPartners } from './render.js';

const list = document.getElementById('partnersList');

async function loadPartners() {
  const response = await fetch('/api/partners');

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const partners = await response.json();
  renderPartners(list, partners);
}

loadPartners().catch((error) => {
  console.error('Failed to load partners:', error);
  list.innerHTML = '<p class="empty-state">Не удалось загрузить данные партнеров.</p>';
});
