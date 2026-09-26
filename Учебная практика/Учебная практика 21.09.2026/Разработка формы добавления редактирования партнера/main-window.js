import { createLogo } from './logo.js';

export class MainWindow {
  constructor(root, partners, onOpenPartner) {
    this.root = root;
    this.partners = partners;
    this.onOpenPartner = onOpenPartner;
    this.list = root.querySelector('#partnersList');
    this.count = root.querySelector('#partnerCount');

    root.querySelector('#addPartnerButton').addEventListener('click', () => this.onOpenPartner(null));
  }

  render() {
    document.title = 'CRM: Реестр партнеров';
    this.count.textContent = `${this.partners.length} партнера`;
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

    const type = document.createElement('span');
    type.className = 'partner-type';
    type.textContent = partner.partner_type;

    const contacts = document.createElement('div');
    contacts.className = 'partner-contacts';
    contacts.append(this.createContact('Телефон', partner.phone));
    contacts.append(this.createContact('Email', partner.email));
    details.append(type, name, contacts);

    const rating = document.createElement('div');
    rating.className = 'partner-rating';
    rating.innerHTML = `<strong>${Number(partner.rating) || 0}</strong><span>рейтинг</span>`;

    const editButton = document.createElement('button');
    editButton.className = 'icon-button';
    editButton.type = 'button';
    editButton.setAttribute('aria-label', `Редактировать ${partner.company_name}`);
    editButton.title = 'Редактировать партнера';
    editButton.textContent = '→';
    editButton.addEventListener('click', () => this.onOpenPartner(partner.id));

    row.append(identity, details, rating, editButton);
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
