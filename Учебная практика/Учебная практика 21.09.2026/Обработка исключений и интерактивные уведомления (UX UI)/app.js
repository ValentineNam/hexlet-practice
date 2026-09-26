import { MainWindow } from './main-window.js';
import { NotificationDialog } from './notifications.js';

const notifications = new NotificationDialog(document.getElementById('messageDialog'));
const mainWindow = new MainWindow(document.getElementById('mainWindow'), notifications);
mainWindow.load();
