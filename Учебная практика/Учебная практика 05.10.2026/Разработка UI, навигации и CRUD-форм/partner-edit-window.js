export class PartnerEditWindow {
  constructor(root, notifications) {
    this.root = root;
    this.notifications = notifications;
    this.form = root.querySelector('#partnerForm');
    this.saveButton = root.querySelector('#saveButton');
    this.mode = new URLSearchParams(location.search).get('mode') === 'edit' ? 'edit' : 'create';
    this.partnerId = Number(new URLSearchParams(location.search).get('partner_id'));
    this.initialSnapshot = '';
    this.busy = false;
    this.promptOpen = false;
  }

  start() {
    this.bindNavigation();
    this.form.addEventListener('submit', (event) => this.save(event));
    window.addEventListener('beforeunload', (event) => {
      if (this.hasChanges() && !this.busy) {
        event.preventDefault();
        event.returnValue = '';
      }
    });
    return this.load();
  }

  async load() {
    const editing = this.mode === 'edit';
    const title = editing ? 'Карточка партнера [Редактирование]' : 'Карточка партнера [Добавление]';
    document.title = `CRM: ${title}`;
    this.root.querySelector('#editMode').textContent = editing ? 'Редактирование' : 'Добавление';
    this.root.querySelector('#editTitle').textContent = title;

    if (!editing) {
      this.snapshot();
      return;
    }
    if (!Number.isInteger(this.partnerId) || this.partnerId <= 0) {
      await this.notifications.alert('error', 'Партнер не выбран', 'Вернитесь в реестр и выберите карточку партнера.');
      location.href = 'index.html';
      return;
    }

    try {
      const response = await fetch(`/api/partners/${this.partnerId}`, { cache: 'no-store' });
      const partner = await response.json();
      if (!response.ok) throw new Error(partner.error || `HTTP ${response.status}`);
      for (const field of this.form.elements) {
        if (field.name && Object.hasOwn(partner, field.name)) {
          field.value = partner[field.name] ?? '';
        }
      }
      this.root.querySelector('#formContext').textContent = `Партнер ID ${partner.id}`;
      this.snapshot();
    } catch (error) {
      await this.notifications.alert('error', 'Не удалось загрузить карточку', `${error.message}\n\nПроверьте настройки PostgreSQL и повторите попытку.`);
      location.href = 'index.html';
    }
  }

  bindNavigation() {
    for (const id of ['backButton', 'cancelButton']) {
      this.root.querySelector(`#${id}`).addEventListener('click', () => this.requestLeave());
    }
    this.root.ownerDocument.querySelector('#homeLink').addEventListener('click', (event) => {
      event.preventDefault();
      this.requestLeave();
    });
  }

  snapshot() {
    this.initialSnapshot = this.serialize();
  }

  serialize() {
    return JSON.stringify([...new FormData(this.form).entries()]);
  }

  hasChanges() {
    return this.initialSnapshot !== '' && this.initialSnapshot !== this.serialize();
  }

  async requestLeave() {
    if (this.promptOpen) return;
    if (!this.hasChanges()) {
      location.href = 'index.html';
      return;
    }
    this.promptOpen = true;
    const leave = await this.notifications.confirm(
      'Есть несохраненные изменения',
      'При выходе введенные данные будут потеряны. Остаться в карточке или покинуть ее?',
    );
    this.promptOpen = false;
    if (leave) {
      this.busy = true;
      location.href = 'index.html';
    }
  }

  validate() {
    const companyName = this.form.elements.company_name;
    const inn = this.form.elements.inn;
    const email = this.form.elements.email;
    const rating = this.form.elements.rating;
    if (!companyName.value.trim()) return [companyName, 'Введите наименование партнера.'];
    if (!/^\d{10}$|^\d{12}$/.test(inn.value.trim())) return [inn, 'ИНН должен содержать 10 или 12 цифр.'];
    if (!email.value.trim() || !email.validity.valid) return [email, 'Введите корректный email.'];
    if (!/^\d+$/.test(rating.value) || Number(rating.value) < 0 || Number(rating.value) > 2147483647) {
      return [rating, 'Рейтинг должен быть целым числом от 0 до 2147483647.'];
    }
    return null;
  }

  async save(event) {
    event.preventDefault();
    if (this.busy) return;
    const validationError = this.validate();
    if (validationError) {
      await this.notifications.alert('error', 'Проверьте данные', validationError[1]);
      validationError[0].focus();
      return;
    }

    const payload = Object.fromEntries(new FormData(this.form).entries());
    payload.rating = Number(payload.rating);
    const endpoint = this.mode === 'edit' ? `/api/partners/${this.partnerId}` : '/api/partners';
    this.busy = true;
    this.saveButton.disabled = true;
    this.saveButton.textContent = 'Сохранение...';
    try {
      const response = await fetch(endpoint, {
        method: this.mode === 'edit' ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      location.href = 'index.html?saved=1';
      return;
    } catch (error) {
      this.busy = false;
      this.saveButton.disabled = false;
      this.saveButton.textContent = 'Сохранить';
      await this.notifications.alert('error', 'Сохранение не выполнено', `${error.message}\n\nПроверьте обязательные поля, уникальность ИНН/email и подключение к базе.`);
    }
  }
}
