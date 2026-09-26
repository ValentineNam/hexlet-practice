import { PartnerEditWindow } from './partner-edit-window.js';

const params = new URLSearchParams(window.location.search);
const mode = params.get('mode') === 'edit' ? 'edit' : 'create';
const partnerId = Number(params.get('partner_id'));
const root = document.getElementById('partnerEditWindow');

function returnToMain() {
  window.location.href = 'index.html';
}

const partnerEditWindow = new PartnerEditWindow(root, returnToMain);
partnerEditWindow.bindEvents();
partnerEditWindow.open(mode, partnerId);
