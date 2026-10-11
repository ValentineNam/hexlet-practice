import { PartnerHistoryWindow } from './partner-history-window.js';

import { NotificationDialog } from './notifications.js';

const notifications = new NotificationDialog(document.querySelector('#messageDialog'));
const partnerHistoryWindow = new PartnerHistoryWindow(document.querySelector('main'), notifications);
partnerHistoryWindow.open();
