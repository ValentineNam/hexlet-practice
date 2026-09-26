import { MainWindow } from './main-window.js';

const partners = Array.isArray(window.partnersDb) ? window.partnersDb : [];
const mainRoot = document.getElementById('mainWindow');
const mainWindow = new MainWindow(mainRoot, partners, openEditWindow);

function openEditWindow(partnerId = null) {
  sessionStorage.setItem('mainWindowScrollY', String(window.scrollY));
  // Режим и ID записи передаются между страницами через query-параметры.
  const target = new URL('partner-edit.html', window.location.href);
  target.searchParams.set('mode', partnerId === null ? 'create' : 'edit');

  if (partnerId !== null) {
    target.searchParams.set('partner_id', String(partnerId));
  }

  window.location.href = target;
}

window.addEventListener('pageshow', () => {
  const savedScrollY = Number(sessionStorage.getItem('mainWindowScrollY') || 0);
  window.scrollTo(0, savedScrollY);
  sessionStorage.removeItem('mainWindowScrollY');
}, { once: true });

mainWindow.render();
