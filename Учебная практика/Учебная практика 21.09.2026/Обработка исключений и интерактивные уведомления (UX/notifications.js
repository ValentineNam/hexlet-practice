export class NotificationDialog {
  constructor(dialog) {
    this.dialog = dialog;
    this.icon = dialog.querySelector('#dialogIcon');
    this.title = dialog.querySelector('#dialogTitle');
    this.message = dialog.querySelector('#dialogMessage');
    this.actions = dialog.querySelector('#dialogActions');
    this.resolveDialog = null;

    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) {
        this.finish(false);
      }
    });
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      this.finish(false);
    });
    this.handleKeydown = (event) => {
      if (event.key === 'Tab') {
        this.keepFocusInside(event);
      }
    };
    dialog.addEventListener('keydown', this.handleKeydown);
  }

  show(type, title, message, actions) {
    this.dialog.dataset.type = type;
    this.icon.textContent = { error: '×', warning: '!', information: 'i' }[type];
    this.title.textContent = title;
    this.message.textContent = message;
    this.actions.replaceChildren();

    actions.forEach((action) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = action.primary ? 'button button-primary' : 'button button-secondary';
      button.textContent = action.label;
      button.addEventListener('click', () => this.finish(action.value));
      this.actions.append(button);
    });

    this.dialog.showModal();
    this.actions.querySelector('button:last-child')?.focus();
    return new Promise((resolve) => {
      this.resolveDialog = resolve;
    });
  }

  alert(type, title, message) {
    return this.show(type, title, message, [
      { label: 'Понятно', value: true, primary: true },
    ]);
  }

  confirm(title, message) {
    return this.show('warning', title, message, [
      { label: 'Остаться', value: false },
      { label: 'Покинуть страницу', value: true, primary: true },
    ]);
  }

  finish(result) {
    if (!this.dialog.open) {
      return;
    }

    this.dialog.close();
    this.resolveDialog?.(result);
    this.resolveDialog = null;
  }

  keepFocusInside(event) {
    const focusable = [...this.dialog.querySelectorAll('button:not(:disabled)')];
    const first = focusable[0];
    const last = focusable.at(-1);

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
}
