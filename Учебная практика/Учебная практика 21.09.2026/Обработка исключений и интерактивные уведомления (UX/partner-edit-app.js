import { PartnerEditWindow } from './partner-edit-window.js';
import { NotificationDialog } from './notifications.js';

const params = new URLSearchParams(window.location.search);
const notifications = new NotificationDialog(document.getElementById('messageDialog'));
const partnerEditWindow = new PartnerEditWindow(
  document.getElementById('partnerEditWindow'),
  notifications,
);

partnerEditWindow.bindEvents();
partnerEditWindow.open(
  params.get('mode') === 'edit' ? 'edit' : 'create',
  Number(params.get('partner_id')),
);
