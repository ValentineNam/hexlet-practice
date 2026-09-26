import { PartnerEditWindow } from './partner-edit-window.js';

const params = new URLSearchParams(window.location.search);
const mode = params.get('mode') === 'edit' ? 'edit' : 'create';
const partnerId = Number(params.get('partner_id'));
const partners = Array.isArray(window.partnersDb) ? window.partnersDb : [];
const partner = partners.find((item) => item.id === partnerId) ?? null;
const editRoot = document.getElementById('partnerEditWindow');

function returnToMain() {
  const cameFromSameApp = document.referrer
    && new URL(document.referrer).origin === window.location.origin;

  if (cameFromSameApp) {
    window.history.back();
    return;
  }

  window.location.href = 'index.html';
}

const partnerEditWindow = new PartnerEditWindow(editRoot, returnToMain);
partnerEditWindow.open(partner, mode);
partnerEditWindow.bindBackButton();
