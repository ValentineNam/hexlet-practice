import { createLogo } from './logo.js';
import { NotificationDialog } from './notifications.js';

export class MainWindow {
  constructor(root, notifications) {
    this.root = root;
    this.notifications = notifications;
    this.list = root.querySelector('#partnersList');
    this.count = root.querySelector('#partnerCount');
    root.querySelector('#addPartnerButton').addEventListener('click', () => {
      window.location.href = 'partner-edit.html?mode=create';
    });
  }

  async load() {
    this.count.textContent = 'Загрузка...';
    this.list.replaceChildren();

    try {
      const response = await fetch('/api/partners', { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || `HTTP ${response.status}`);
      }
      this.render(result);
    } catch (error) {
      this.count.textContent = 'Ошибка загрузки';
      this.renderMessage('Не удалось получить список партнеров.');
      await this.notifications.alert(
        'error',
        'Не удалось загрузить реестр',
        `${error.message}\n\nПроверьте, что сервер запущен, параметры подключения к БД указаны верно, а база данных доступна. Затем обновите страницу.`,
      );
    }

    if (new URLSearchParams(window.location.search).get('saved') === '1') {
      await this.notifications.alert(
        'information',
        'Данные сохранены',
        'Изменения записаны в базу данных. Реестр обновлен актуальными данными.',
      );
      window.history.replaceState({}, '', window.location.pathname);
    }
  }

  render(partners) {
    this.list.replaceChildren();
    this.count.textContent = `${partners.length} партнеров`;

    if (partners.length === 0) {
      this.renderMessage('В базе пока нет партнеров. Добавьте первую запись.');
      return;
    }

    partners.forEach((partner) => this.list.append(this.createPartnerRow(partner)));
  }

  renderMessage(message) {
    const notice = document.createElement('p');
    notice.className = 'empty-state';
    notice.textContent = message;
    this.list.replaceChildren(notice);
  }

  createPartnerRow(partner) {
    const row = document.createElement('article');
    row.className = 'partner-row';
    const identity = document.createElement('div');
    identity.className = 'partner-identity';
    identity.append(createLogo(partner));

    const details = document.createElement('div');
    details.className = 'partner-details';
    const type = document.createElement('span');
    type.className = 'partner-type';
    type.textContent = partner.partner_type;
    const name = document.createElement('h2');
    name.className = 'partner-name';
    name.textContent = partner.company_name;
    const contacts = document.createElement('div');
    contacts.className = 'partner-contacts';
    contacts.append(this.createContact('Телефон', partner.phone));
    contacts.append(this.createContact('Email', partner.email));
    details.append(type, name, contacts);

    const discount = document.createElement('div');
    discount.className = 'partner-discount';
    const value = document.createElement('strong');
    value.textContent = `${Number(partner.discount) || 0}%`;
    const label = document.createElement('span');
    label.textContent = 'скидка';
    discount.append(value, label);

    const editButton = document.createElement('button');
    editButton.className = 'icon-button';
    editButton.type = 'button';
    editButton.textContent = '→';
    editButton.title = 'Редактировать партнера';
    editButton.setAttribute('aria-label', `Редактировать ${partner.company_name}`);
    editButton.addEventListener('click', () => {
      window.location.href = `partner-edit.html?mode=edit&partner_id=${encodeURIComponent(partner.id)}`;
    });

    row.append(identity, details, discount, editButton);
    return row;
  }

  createContact(label, value) {
    const item = document.createElement('span');
    item.className = 'partner-contact';
    const caption = document.createElement('span');
    caption.textContent = `${label}: `;
    const text = document.createElement('span');
    text.textContent = value || 'Не указано';
    item.append(caption, text);
    return item;
  }
}
