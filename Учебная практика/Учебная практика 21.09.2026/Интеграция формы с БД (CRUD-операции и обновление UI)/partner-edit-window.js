export class PartnerEditWindow {
  constructor(root, onBack) {
    this.root = root;
    this.onBack = onBack;
    this.form = root.querySelector('#partnerForm');
    this.loadError = root.querySelector('#loadError');
    this.saveError = root.querySelector('#saveError');
    this.submitButton = this.form.querySelector('[type="submit"]');
    this.mode = 'create';
    this.partnerId = null;

    root.querySelector('#backButton').addEventListener('click', onBack);
    root.querySelector('#cancelButton').addEventListener('click', onBack);
  }

  bindEvents() {
    this.form.addEventListener('submit', (event) => this.save(event));
  }

  async open(mode, partnerId) {
    this.mode = mode;
    this.partnerId = mode === 'edit' && Number.isInteger(partnerId) ? partnerId : null;
    const isEditing = this.mode === 'edit';
    const title = isEditing ? 'Карточка партнера [Редактирование]' : 'Карточка партнера [Добавление]';
    this.root.querySelector('#editMode').textContent = isEditing ? 'Редактирование' : 'Добавление';
    this.root.querySelector('#editTitle').textContent = title;
    document.title = `CRM: ${title}`;
    this.root.querySelector('#formContext').textContent = isEditing
      ? `Партнер ID ${this.partnerId ?? 'не указан'}`
      : 'Новая запись';

    if (!isEditing) {
      this.form.reset();
      return;
    }

    if (this.partnerId === null) {
      this.showLoadError('Не указан корректный идентификатор партнера. Вернитесь в реестр и выберите запись.');
      return;
    }

    try {
      const response = await fetch(`/api/partners/${this.partnerId}`, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || `HTTP ${response.status}`);
      }
      this.fill(result);
    } catch (error) {
      this.showLoadError(`Не удалось загрузить партнера: ${error.message}`);
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
    this.saveError.hidden = true;

    if (!this.form.reportValidity()) {
      return;
    }

    const payload = Object.fromEntries(new FormData(this.form).entries());
    payload.rating = Number(payload.rating);
    const endpoint = this.mode === 'edit'
      ? `/api/partners/${this.partnerId}`
      : '/api/partners';
    const method = this.mode === 'edit' ? 'PUT' : 'POST';
    this.submitButton.disabled = true;
    this.submitButton.textContent = 'Сохранение...';

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
      window.location.href = 'index.html?saved=1';
    } catch (error) {
      this.showSaveError(`Не удалось сохранить данные: ${error.message}`);
    } finally {
      this.submitButton.disabled = false;
      this.submitButton.innerHTML = '<span class="button-icon" aria-hidden="true">✓</span>Сохранить';
    }
  }

  showLoadError(message) {
    this.loadError.textContent = message;
    this.loadError.hidden = false;
    this.form.hidden = true;
  }

  showSaveError(message) {
    this.saveError.textContent = message;
    this.saveError.hidden = false;
  }
}
