import { NotificationDialog } from './notifications.js';
import { PartnerEditWindow } from './partner-edit-window.js';

const notificationDialog = new NotificationDialog(document.getElementById('messageDialog'));
const partnerEditWindow = new PartnerEditWindow(
  document.getElementById('editWindow'),
  notificationDialog,
);
partnerEditWindow.start();
