import { NotificationDialog } from './notifications.js';

export class MainWindow {
  constructor(root, notifications) {
    this.root = root;
    this.notifications = notifications;
    this.list = root.querySelector('#partnersList');
    this.count = root.querySelector('#partnerCount');
    this.historyButton = root.querySelector('#historyButton');
    this.selectedPartnerId = null;

    root.querySelector('#addPartnerButton').addEventListener('click', () => {
      window.location.href = 'partner-edit.html?mode=create';
    });
    this.historyButton.addEventListener('click', () => {
      if (this.selectedPartnerId !== null) {
        window.location.href = `history.html?partner_id=${encodeURIComponent(this.selectedPartnerId)}`;
      }
    });
    this.list.addEventListener('change', (event) => {
      if (!event.target.matches('input[name="selectedPartner"]')) return;
      this.selectedPartnerId = Number(event.target.value);
      this.historyButton.disabled = false;
      this.list.querySelectorAll('.partner-row').forEach((row) => {
        row.classList.toggle('is-selected', row.contains(event.target));
      });
    });
  }

  async load() {
    this.count.textContent = 'Загрузка...';
    this.list.replaceChildren();
    try {
      const response = await fetch('/api/partners', { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      this.render(result);
    } catch (error) {
      this.count.textContent = 'Ошибка загрузки';
      this.renderMessage('Не удалось загрузить реестр.');
      await this.notifications.alert('error', 'Ошибка загрузки', `${error.message}\n\nПроверьте сервер, .env и доступность PostgreSQL, затем обновите страницу.`);
    }
    if (new URLSearchParams(location.search).get('saved') === '1') {
      await this.notifications.alert('information', 'Изменения сохранены', 'Данные партнера записаны в базу, список обновлен.');
      history.replaceState({}, '', location.pathname);
    }
  }

  render(partners) {
    this.list.replaceChildren();
    this.count.textContent = `${partners.length} партнеров`;
    if (!partners.length) {
      this.renderMessage('В базе пока нет партнеров.');
      return;
    }
    partners.forEach((partner) => this.list.append(this.createRow(partner)));
  }

  createRow(partner) {
    const row = document.createElement('article');
    row.className = 'partner-row';
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'selectedPartner';
    radio.value = String(partner.id);
    radio.setAttribute('aria-label', `Выбрать ${partner.company_name}`);
    const type = document.createElement('span');
    type.className = 'partner-type';
    type.textContent = partner.partner_type;
    const identity = document.createElement('span');
    identity.className = 'partner-mark';
    identity.textContent = partner.company_name.match(/[A-Za-zА-Яа-яЁё]/u)?.[0]?.toUpperCase() || 'П';
    const details = document.createElement('span');
    details.className = 'partner-details';
    const name = document.createElement('strong');
    name.textContent = partner.company_name;
    const contacts = document.createElement('span');
    contacts.className = 'partner-contacts';
    contacts.textContent = `${partner.phone || 'Телефон не указан'} · ${partner.email}`;
    details.append(name, contacts);
    const discount = document.createElement('span');
    discount.className = 'partner-discount';
    discount.textContent = `${partner.discount}%`;
    const edit = document.createElement('a');
    edit.className = 'icon-button';
    edit.href = `partner-edit.html?mode=edit&partner_id=${encodeURIComponent(partner.id)}`;
    edit.textContent = '↗';
    edit.setAttribute('aria-label', `Редактировать ${partner.company_name}`);
    row.append(radio, identity, type, details, discount, edit);
    return row;
  }

  renderMessage(message) {
    const notice = document.createElement('p');
    notice.className = 'empty-state';
    notice.textContent = message;
    this.list.replaceChildren(notice);
  }
}
