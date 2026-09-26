export class PartnerEditWindow {
  constructor(root, notifications) {
    this.root = root;
    this.notifications = notifications;
    this.form = root.querySelector('#partnerForm');
    this.submitButton = root.querySelector('#saveButton');
    this.mode = 'create';
    this.partnerId = null;
    this.initialValues = '';
    this.isSaving = false;
    this.navigationPromptOpen = false;

    root.querySelector('#backButton').addEventListener('click', () => this.requestLeave());
    root.querySelector('#cancelButton').addEventListener('click', () => this.requestLeave());
    root.ownerDocument.querySelector('#homeLink').addEventListener('click', (event) => {
      event.preventDefault();
      this.requestLeave();
    });
    this.form.addEventListener('input', () => this.updateDirtyState());
    this.form.addEventListener('change', () => this.updateDirtyState());
    window.addEventListener('beforeunload', (event) => {
      if (this.hasUnsavedChanges() && !this.isSaving) {
        event.preventDefault();
        event.returnValue = '';
      }
    });
  }

  bindEvents() {
    this.form.addEventListener('submit', (event) => this.save(event));
  }

  async open(mode, partnerId) {
    this.mode = mode;
    this.partnerId = mode === 'edit' && Number.isInteger(partnerId) && partnerId > 0
      ? partnerId
      : null;
    const isEditing = this.mode === 'edit';
    const title = isEditing ? 'Карточка партнера [Редактирование]' : 'Карточка партнера [Добавление]';
    this.root.querySelector('#editMode').textContent = isEditing ? 'Редактирование' : 'Добавление';
    this.root.querySelector('#editTitle').textContent = title;
    this.root.querySelector('#formContext').textContent = isEditing
      ? `Партнер ID ${this.partnerId ?? 'не указан'}`
      : 'Новая запись';
    document.title = `CRM: ${title}`;

    if (!isEditing) {
      this.form.reset();
      this.captureInitialValues();
      return;
    }

    if (this.partnerId === null) {
      await this.showLoadError('Не указан корректный идентификатор партнера. Вернитесь в реестр и выберите запись.');
      return;
    }

    try {
      const response = await fetch(`/api/partners/${this.partnerId}`, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || `HTTP ${response.status}`);
      }
      this.fill(result);
      this.captureInitialValues();
    } catch (error) {
      await this.showLoadError(
        `Не удалось загрузить данные: ${error.message}\n\nПроверьте подключение к серверу и базе данных. Вернитесь в реестр и повторите попытку.`,
      );
    }
  }

  fill(partner) {
    this.form.elements.company_name.value = partner.company_name || '';
    this.form.elements.inn.value = partner.inn || '';
    this.form.elements.partner_type.value = partner.partner_type || '';
    this.form.elements.rating.value = partner.rating ?? '';
    this.form.elements.address.value = partner.address || '';
    this.form.elements.director.value = partner.director || '';
    this.form.elements.phone.value = partner.phone || '';
    this.form.elements.email.value = partner.email || '';
  }

  async save(event) {
    event.preventDefault();

    if (this.isSaving) {
      return;
    }

    const validationError = this.validateForm();
    if (validationError) {
      await this.notifications.alert('error', 'Проверьте данные партнера', validationError.message);
      validationError.field.focus();
      return;
    }

    const payload = Object.fromEntries(new FormData(this.form).entries());
    payload.company_name = payload.company_name.trim();
    payload.inn = payload.inn.trim();
    payload.email = payload.email.trim();
    payload.rating = Number(payload.rating);
    const endpoint = this.mode === 'edit'
      ? `/api/partners/${this.partnerId}`
      : '/api/partners';
    const method = this.mode === 'edit' ? 'PUT' : 'POST';
    this.setSaving(true);

    try {
      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || `HTTP ${response.status}`);
      }
      this.isSaving = true;
      window.location.href = 'index.html?saved=1';
    } catch (error) {
      await this.notifications.alert(
        'error',
        'Не удалось сохранить данные',
        `${error.message}\n\nПроверьте обязательные поля и уникальность email/ИНН. Если ошибка связана с подключением, убедитесь, что сервер и PostgreSQL запущены, затем повторите сохранение. Введенные данные останутся в форме.`,
      );
    } finally {
      this.setSaving(false);
    }
  }

  validateForm() {
    const companyName = this.form.elements.company_name;
    const inn = this.form.elements.inn;
    const partnerType = this.form.elements.partner_type;
    const rating = this.form.elements.rating;
    const email = this.form.elements.email;

    if (!companyName.value.trim()) {
      return { field: companyName, message: 'Введите наименование партнера, затем повторите сохранение.' };
    }
    if (!/^\d{10}$|^\d{12}$/.test(inn.value.trim())) {
      return { field: inn, message: 'ИНН должен состоять ровно из 10 или 12 цифр. Удалите пробелы и другие символы.' };
    }
    if (!partnerType.value) {
      return { field: partnerType, message: 'Выберите тип партнера из выпадающего списка.' };
    }
    if (!/^\d+$/.test(rating.value) || Number(rating.value) < 0 || Number(rating.value) > 5) {
      return { field: rating, message: 'Рейтинг должен быть целым числом от 0 до 5. Исправьте значение и повторите сохранение.' };
    }
    if (!email.value.trim() || !email.validity.valid) {
      return { field: email, message: 'Укажите корректный email компании, например name@company.ru.' };
    }

    return null;
  }

  async requestLeave() {
    if (this.navigationPromptOpen) {
      return;
    }

    if (!this.hasUnsavedChanges()) {
      window.location.href = 'index.html';
      return;
    }

    this.navigationPromptOpen = true;
    const leave = await this.notifications.confirm(
      'Есть несохраненные изменения',
      'Если покинуть карточку сейчас, все внесенные изменения будут потеряны без возможности восстановления. Продолжить редактирование или покинуть страницу?',
    );
    this.navigationPromptOpen = false;

    if (leave) {
      this.isSaving = true;
      window.location.href = 'index.html';
    }
  }

  hasUnsavedChanges() {
    return this.form && this.initialValues !== '' && this.serializeForm() !== this.initialValues;
  }

  serializeForm() {
    return JSON.stringify([...new FormData(this.form).entries()]);
  }

  captureInitialValues() {
    this.initialValues = this.serializeForm();
  }

  updateDirtyState() {
    this.root.dataset.dirty = String(this.hasUnsavedChanges());
  }

  setSaving(isSaving) {
    this.isSaving = isSaving;
    this.submitButton.disabled = isSaving;
    this.submitButton.innerHTML = isSaving
      ? 'Сохранение...'
      : '<span class="button-icon" aria-hidden="true">✓</span>Сохранить';
  }

  async showLoadError(message) {
    this.form.hidden = true;
    await this.notifications.alert('error', 'Не удалось открыть карточку', message);
  }
}
