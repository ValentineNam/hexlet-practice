export class PartnerHistoryWindow {
  constructor(root) {
    this.root = root;
    this.partnerId = Number(new URLSearchParams(location.search).get('partner_id'));
    this.title = root.querySelector('#historyTitle');
    this.message = root.querySelector('#historyMessage');
    this.table = root.querySelector('#historyTableWrap');
  }

  async open() {
    if (!Number.isInteger(this.partnerId) || this.partnerId <= 0) {
      this.showMessage('Не выбран партнер. Вернитесь в реестр и выберите запись.', true);
      return;
    }

    try {
      const response = await fetch(`/api/partners/${this.partnerId}/history`, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      this.render(result);
    } catch (error) {
      this.showMessage(`Не удалось загрузить историю: ${error.message}. Проверьте соединение и повторите попытку.`, true);
    }
  }

  render(result) {
    this.title.textContent = `История реализации продукции — ${result.partner.company_name}`;
    document.title = `CRM: ${this.title.textContent}`;
    this.root.querySelector('#partnerName').textContent = result.partner.company_name;
    this.root.querySelector('#partnerMark').textContent = result.partner.company_name.match(/[A-Za-zА-Яа-яЁё]/u)?.[0]?.toUpperCase() || 'П';
    this.root.querySelector('#historyCount').textContent = `${result.rows.length} позиций`;
    this.root.querySelector('#partnerSummary').hidden = false;

    if (!result.rows.length) {
      this.showMessage('Для этого партнера пока нет истории реализации.');
      return;
    }

    const rows = this.root.querySelector('#historyRows');
    rows.replaceChildren();
    result.rows.forEach((item) => rows.append(this.createRow(item)));
    this.message.hidden = true;
    this.table.hidden = false;
  }

  createRow(item) {
    const row = document.createElement('tr');
    const product = document.createElement('th');
    product.scope = 'row';
    product.textContent = item.product_name;
    const quantity = document.createElement('td');
    quantity.textContent = Number(item.quantity).toLocaleString('ru-RU');
    const date = document.createElement('td');
    date.textContent = item.sale_date;
    row.append(product, quantity, date);
    return row;
  }

  showMessage(text, isError = false) {
    this.message.textContent = text;
    this.message.classList.toggle('error-message', isError);
    this.message.hidden = false;
    this.table.hidden = true;
  }
}
