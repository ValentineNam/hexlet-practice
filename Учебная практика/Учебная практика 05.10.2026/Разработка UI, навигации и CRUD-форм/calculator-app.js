const form = document.getElementById('calculatorForm');
const productSelect = form.elements.product_type_id;
const materialSelect = form.elements.material_type_id;
const button = document.getElementById('calculateButton');
const panel = document.getElementById('resultPanel');
const valueNode = document.getElementById('resultValue');
const messageNode = document.getElementById('resultMessage');

function showResult(state, value, message) {
  panel.dataset.state = state;
  valueNode.textContent = value;
  messageNode.textContent = message;
}

async function loadCatalogs() {
  try {
    const response = await fetch('/api/material/catalogs', { cache: 'no-store' });
    const catalogs = await response.json();
    if (!response.ok) throw new Error(catalogs.error || `HTTP ${response.status}`);
    populate(productSelect, catalogs.product_types, (item) => `Тип ${item.id} · ×${item.coefficient}`);
    populate(materialSelect, catalogs.material_types, (item) => `Материал ${item.id} · брак ${item.scrap_percentage}%`);
    productSelect.disabled = false;
    materialSelect.disabled = false;
    button.disabled = false;
  } catch (error) {
    showResult('error', 'Ошибка', `Не удалось загрузить справочники: ${error.message}`);
  }
}

function populate(select, values, labelFor) {
  select.replaceChildren();
  const placeholder = new Option('Выберите тип', '', true, true);
  placeholder.disabled = true;
  select.add(placeholder);
  values.forEach((value) => select.add(new Option(labelFor(value), value.id)));
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  const payload = Object.fromEntries(new FormData(form).entries());
  for (const key of ['product_type_id', 'material_type_id', 'quantity']) {
    payload[key] = Number(payload[key]);
  }
  button.disabled = true;

  try {
    const response = await fetch('/api/material/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    if (result.material_requirement === -1) {
      showResult('error', 'Расчет невозможен', 'Проверьте ID типов, положительные параметры и количество больше нуля.');
      return;
    }
    showResult('success', `${result.material_requirement.toLocaleString('ru-RU')} ед.`, 'Материал с учетом брака; результат округлен вверх.');
  } catch (error) {
    showResult('error', 'Ошибка', `Не удалось рассчитать материал: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

loadCatalogs();
