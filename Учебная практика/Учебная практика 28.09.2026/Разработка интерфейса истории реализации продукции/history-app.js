const params = new URLSearchParams(window.location.search);
const partnerId = Number(params.get('partner_id'));
const title = document.getElementById('historyTitle');
const summary = document.getElementById('partnerSummary');
const message = document.getElementById('historyMessage');
const tableWrap = document.getElementById('historyTableWrap');
const rowsRoot = document.getElementById('historyRows');

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle('error-message', isError);
  message.hidden = false;
  tableWrap.hidden = true;
}

async function loadHistory() {
  if (!Number.isInteger(partnerId) || partnerId <= 0) {
    document.title = 'CRM: История реализации продукции';
    showMessage('Не выбран партнер. Вернитесь в реестр и откройте историю продаж для нужной записи.', true);
    return;
  }

  try {
    const response = await fetch(`/api/partners/${partnerId}/history`, { cache: 'no-store' });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }

    title.textContent = `История реализации продукции — ${result.partner.company_name}`;
    document.title = `CRM: ${title.textContent}`;
    document.getElementById('partnerName').textContent = result.partner.company_name;
    const shortName = result.partner.company_name
      .replace(/^(?:ООО|АО|ЗАО|ПАО|ИП)\s*/i, '')
      .replace(/^[^A-Za-zА-Яа-яЁё]*/, '');
    document.getElementById('partnerMark').textContent = shortName[0]?.toUpperCase() || 'П';
    document.getElementById('shipmentCount').textContent = `${result.rows.length} позиций`;
    summary.hidden = false;

    if (result.rows.length === 0) {
      showMessage('Для этого партнера пока нет истории реализации.');
      return;
    }

    rowsRoot.replaceChildren();
    result.rows.forEach((item) => rowsRoot.append(createRow(item)));
    message.hidden = true;
    tableWrap.hidden = false;
  } catch (error) {
    showMessage(`Не удалось загрузить историю: ${error.message}. Проверьте соединение и повторите попытку.`, true);
  }
}

function createRow(item) {
  const row = document.createElement('tr');
  const product = document.createElement('th');
  product.scope = 'row';
  product.textContent = item.product_name;
  const quantity = document.createElement('td');
  quantity.className = 'quantity-cell';
  quantity.textContent = Number(item.quantity).toLocaleString('ru-RU');
  const date = document.createElement('td');
  date.textContent = item.sale_date;
  row.append(product, quantity, date);
  return row;
}

loadHistory();
