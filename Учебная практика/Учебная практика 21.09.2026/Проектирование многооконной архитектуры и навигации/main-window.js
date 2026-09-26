import { createLogo } from './logo.js';

export class MainWindow {
  constructor(root, partners, onOpenPartner) {
    this.root = root;
    this.partners = partners;
    this.onOpenPartner = onOpenPartner;
    this.list = root.querySelector('#partnersList');
    this.count = root.querySelector('#partnerCount');
    this.addButton = root.querySelector('#addPartnerButton');

    this.addButton.addEventListener('click', () => this.onOpenPartner(null));
  }

  render() {
    this.root.querySelector('#mainTitle').textContent = 'Реестр партнеров';
    document.title = 'CRM: Реестр партнеров';
    this.count.textContent = `${this.partners.length} партнеров`;
    this.list.replaceChildren();

    if (this.partners.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'Список партнеров пока пуст.';
      this.list.append(empty);
      return;
    }

    this.partners.forEach((partner) => this.list.append(this.createPartnerRow(partner)));
  }

  createPartnerRow(partner) {
    const row = document.createElement('article');
    row.className = 'partner-row';

    const identity = document.createElement('div');
    identity.className = 'partner-identity';
    identity.append(createLogo(partner));

    const details = document.createElement('div');
    details.className = 'partner-details';

    const name = document.createElement('h2');
    name.className = 'partner-name';
    name.textContent = partner.company_name;

    const contacts = document.createElement('div');
    contacts.className = 'partner-contacts';
    contacts.append(this.createContact('Телефон', partner.phone));
    contacts.append(this.createContact('Email', partner.email));
    details.append(name, contacts);

    const discount = document.createElement('div');
    discount.className = 'discount';
    discount.innerHTML = `<strong>${Number(partner.discount) || 0}%</strong><span>скидка</span>`;

    const editButton = document.createElement('button');
    editButton.className = 'icon-button';
    editButton.type = 'button';
    editButton.setAttribute('aria-label', `Открыть карточку: ${partner.company_name}`);
    editButton.title = 'Открыть карточку партнера';
    editButton.textContent = '→';
    editButton.addEventListener('click', () => this.onOpenPartner(partner.id));

    row.append(identity, details, discount, editButton);
    return row;
  }

  createContact(label, value) {
    const contact = document.createElement('span');
    contact.className = 'partner-contact';
    const caption = document.createElement('span');
    caption.textContent = `${label}: `;
    const content = document.createElement('span');
    content.textContent = value;
    contact.append(caption, content);
    return contact;
  }
}
