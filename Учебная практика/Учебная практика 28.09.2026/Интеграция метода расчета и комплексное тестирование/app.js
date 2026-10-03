const form = document.getElementById('calculatorForm');
const productType = document.getElementById('productTypeId');
const materialType = document.getElementById('materialTypeId');
const calculateButton = document.getElementById('calculateButton');
const resultPanel = document.getElementById('resultPanel');
const resultValue = document.getElementById('resultValue');
const resultMessage = document.getElementById('resultMessage');
let catalogsReady = false;

async function loadCatalogs() {
  try {
    const response = await fetch('/api/material/catalogs', { cache: 'no-store' });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }

    fillOptions(
      productType,
      result.product_types,
      (item) => `Тип ${item.id} · коэффициент ${item.coefficient}`,
    );
    fillOptions(
      materialType,
      result.material_types,
      (item) => `Материал ${item.id} · брак ${item.scrap_percentage}%`,
    );
    document.getElementById('productCoefficientHint').textContent = 'Коэффициент берется из справочника типа продукции.';
    document.getElementById('materialScrapHint').textContent = 'Процент брака выбранного материала будет учтен автоматически.';
    productType.disabled = false;
    materialType.disabled = false;
    calculateButton.disabled = false;
    catalogsReady = true;
  } catch (error) {
    setResult('error', '—', `Не удалось загрузить справочники: ${error.message}. Обновите страницу или проверьте сервер.`);
  }
}

function fillOptions(select, items, labelFor) {
  select.replaceChildren();
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Выберите тип';
  placeholder.disabled = true;
  placeholder.selected = true;
  select.append(placeholder);

  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = String(item.id);
    option.textContent = labelFor(item);
    select.append(option);
  });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!catalogsReady || !form.reportValidity()) {
    return;
  }

  const payload = Object.fromEntries(new FormData(form).entries());
  payload.product_type_id = Number(payload.product_type_id);
  payload.material_type_id = Number(payload.material_type_id);
  payload.quantity = Number(payload.quantity);
  payload.param_1 = Number(payload.param_1);
  payload.param_2 = Number(payload.param_2);

  calculateButton.disabled = true;
  calculateButton.textContent = 'Расчет...';

  try {
    const response = await fetch('/api/material/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }

    if (result.material_requirement === -1) {
      setResult('error', 'Ошибка', 'Расчет невозможен. Проверьте типы, положительные параметры и количество больше нуля.');
      return;
    }

    setResult('success', `${result.material_requirement.toLocaleString('ru-RU')} ед.`, 'Расход с учетом процента брака. Результат округлен вверх.');
  } catch (error) {
    setResult('error', 'Ошибка', `Не удалось выполнить расчет: ${error.message}. Повторите попытку.`);
  } finally {
    calculateButton.disabled = false;
    calculateButton.innerHTML = '<span class="button-icon" aria-hidden="true">∑</span>Рассчитать';
  }
});

function setResult(state, value, message) {
  resultPanel.dataset.state = state;
  resultValue.textContent = value;
  resultMessage.textContent = message;
}

loadCatalogs();
