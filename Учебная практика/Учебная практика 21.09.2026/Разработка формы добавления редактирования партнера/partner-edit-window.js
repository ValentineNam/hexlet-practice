export class PartnerEditWindow {
  constructor(root, onBack) {
    this.root = root;
    this.onBack = onBack;
    this.form = root.querySelector('#partnerForm');
    this.backButton = root.querySelector('#backButton');
    this.cancelButton = root.querySelector('#cancelButton');
    this.status = root.querySelector('#formStatus');
    this.missingPartner = root.querySelector('#missingPartner');
  }

  bindEvents() {
    this.backButton.addEventListener('click', this.onBack);
    this.cancelButton.addEventListener('click', this.onBack);
    this.form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.status.textContent = 'Поля заполнены. Сохранение будет подключено на следующем этапе.';
    });
  }

  open(partner, mode) {
    const isEditing = mode === 'edit';
    const title = isEditing ? 'Карточка партнера [Редактирование]' : 'Карточка партнера [Добавление]';
    this.root.querySelector('#editMode').textContent = isEditing ? 'Редактирование' : 'Добавление';
    this.root.querySelector('#editTitle').textContent = title;
    document.title = `CRM: ${title}`;

    if (isEditing && partner === null) {
      this.form.hidden = true;
      this.missingPartner.hidden = false;
      this.root.querySelector('#formContext').textContent = 'Запись не найдена';
      return;
    }

    this.missingPartner.hidden = true;
    this.form.hidden = false;
    this.root.querySelector('#formContext').textContent = isEditing
      ? `Партнер ID ${partner.id}`
      : 'Новая запись';

    if (partner === null) {
      this.form.reset();
      return;
    }

    this.form.elements.company_name.value = partner.company_name;
    this.form.elements.partner_type.value = partner.partner_type;
    this.form.elements.rating.value = partner.rating;
    this.form.elements.address.value = partner.address;
    this.form.elements.director.value = partner.director;
    this.form.elements.phone.value = partner.phone;
    this.form.elements.email.value = partner.email;
  }
}
