export class PartnerEditWindow {
  constructor(root, onBack) {
    this.root = root;
    this.onBack = onBack;
    this.currentPartnerId = null;
    this.backButton = root.querySelector('#backButton');
  }

  bindBackButton() {
    this.backButton.addEventListener('click', this.onBack);
  }

  open(partner, mode) {
    this.currentPartnerId = partner?.id ?? null;
    const isEditing = mode === 'edit';
    const displayMode = isEditing ? 'Редактирование' : 'Добавление';
    const title = isEditing ? 'Карточка партнера [Редактирование]' : 'Карточка партнера [Добавление]';

    this.root.querySelector('#editMode').textContent = displayMode;
    this.root.querySelector('#editTitle').textContent = title;
    this.root.querySelector('#editContextLabel').textContent = isEditing
      ? partner ? `Партнер ID ${partner.id}` : 'Партнер не найден'
      : 'Новая запись';
    this.root.querySelector('#editPartnerName').textContent = partner?.company_name ?? (isEditing ? 'Партнер не найден' : 'Новый партнер');
    document.title = `CRM: ${title}`;
  }
}
