import { createLogo } from './logo.js';

export class MainWindow {
  constructor(root) {
    this.root = root;
    this.list = root.querySelector('#partnersList');
    this.count = root.querySelector('#partnerCount');
    this.historyButton = root.querySelector('#historyButton');
    this.selectedPartnerId = null;

    this.list.addEventListener('change', (event) => {
      if (event.target.matches('input[name="selectedPartner"]')) {
        this.selectedPartnerId = Number(event.target.value);
        this.historyButton.disabled = false;
        this.list.querySelectorAll('.partner-option').forEach((option) => {
          option.classList.toggle('is-selected', option.contains(event.target));
        });
      }
    });

    this.historyButton.addEventListener('click', () => {
      if (this.selectedPartnerId === null) {
        return;
      }
      window.location.href = `history.html?partner_id=${encodeURIComponent(this.selectedPartnerId)}`;
    });
  }

  async load() {
    this.list.replaceChildren();
    this.count.textContent = 'Загрузка...';

    try {
      const response = await fetch('/api/partners', { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || `HTTP ${response.status}`);
      }
      this.render(result);
    } catch (error) {
      this.count.textContent = 'Нет подключения';
      this.renderMessage(`Не удалось загрузить партнеров: ${error.message}`);
    }
  }

  render(partners) {
    this.list.replaceChildren();
    this.count.textContent = `${partners.length} партнеров`;

    if (partners.length === 0) {
      this.renderMessage('В базе пока нет партнеров.');
      return;
    }

    partners.forEach((partner) => this.list.append(this.createPartnerOption(partner)));
  }

  createPartnerOption(partner) {
    const label = document.createElement('label');
    label.className = 'partner-option';

    const selector = document.createElement('input');
    selector.type = 'radio';
    selector.name = 'selectedPartner';
    selector.value = String(partner.id);
    selector.setAttribute('aria-label', `Выбрать ${partner.company_name}`);

    const identity = document.createElement('span');
    identity.className = 'partner-identity';
    identity.append(createLogo(partner));

    const details = document.createElement('span');
    details.className = 'partner-details';
    const type = document.createElement('span');
    type.className = 'partner-type';
    type.textContent = partner.partner_type;
    const name = document.createElement('span');
    name.className = 'partner-name';
    name.textContent = partner.company_name;
    const contacts = document.createElement('span');
    contacts.className = 'partner-contacts';
    contacts.append(this.createContact('Телефон', partner.phone));
    contacts.append(this.createContact('Email', partner.email));
    details.append(type, name, contacts);

    const discount = document.createElement('span');
    discount.className = 'partner-discount';
    const discountValue = document.createElement('strong');
    discountValue.textContent = `${Number(partner.discount) || 0}%`;
    const discountLabel = document.createElement('span');
    discountLabel.textContent = 'скидка';
    discount.append(discountValue, discountLabel);

    label.append(selector, identity, details, discount);
    return label;
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

  renderMessage(message) {
    const notice = document.createElement('p');
    notice.className = 'empty-state';
    notice.textContent = message;
    this.list.replaceChildren(notice);
  }
}
