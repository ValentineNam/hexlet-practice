import { createLogo } from './logo.js';

export function renderPartners(list, partners) {
  list.innerHTML = '';

  partners.forEach((partner) => {
    const card = document.createElement('article');
    card.className = 'partner-card';

    const logo = createLogo(partner);

    const meta = document.createElement('div');
    meta.className = 'partner-meta';

    const title = document.createElement('div');
    title.className = 'partner-line';
    title.innerHTML = `<span class="label">${partner.company_name}</span>`;

    const director = document.createElement('div');
    director.className = 'partner-line';
    director.textContent = `Директор: ${partner.director}`;

    const phone = document.createElement('div');
    phone.className = 'partner-line';
    phone.textContent = partner.phone;

    const email = document.createElement('div');
    email.className = 'partner-line';
    email.textContent = partner.email;

    meta.append(title, director, phone, email);

    const discount = document.createElement('div');
    discount.className = 'partner-discount';
    discount.textContent = `${partner.discount}%`;

    card.append(logo, meta, discount);
    list.appendChild(card);
  });
}
