import { PartnerEditWindow } from './partner-edit-window.js';

const params = new URLSearchParams(window.location.search);
const mode = params.get('mode') === 'edit' ? 'edit' : 'create';
const partnerId = Number(params.get('partner_id'));
const partners = Array.isArray(window.partnersDb) ? window.partnersDb : [];
const partner = partners.find((item) => item.id === partnerId) ?? null;
const editRoot = document.querySelector('main');

function returnToMain() {
  const previousUrl = document.referrer ? new URL(document.referrer) : null;
  const cameFromRegistry = previousUrl?.origin === window.location.origin
    && previousUrl.pathname.endsWith('/index.html');

  if (cameFromRegistry) {
    window.history.back();
    return;
  }

  window.location.href = 'index.html';
}

const partnerEditWindow = new PartnerEditWindow(editRoot, returnToMain);
partnerEditWindow.open(partner, mode);
partnerEditWindow.bindEvents();
