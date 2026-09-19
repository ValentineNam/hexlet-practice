import { renderPartners } from './render.js';

const list = document.getElementById('partnersList');

function loadPartners() {
  const partners = Array.isArray(window.partnersDb) ? window.partnersDb : [];

  if (!partners.length) {
    list.innerHTML = '<p class="empty-state">Нет данных партнеров.</p>';
    return;
  }

  renderPartners(list, partners);
}

loadPartners();
