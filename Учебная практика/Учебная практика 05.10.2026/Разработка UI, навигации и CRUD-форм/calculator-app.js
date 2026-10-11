import { NotificationDialog } from './notifications.js';

const notifications = new NotificationDialog(document.querySelector('#messageDialog'));
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

async function showError(message, steps) {
  showResult('error', 'Ошибка', message);
  await notifications.alert('error', 'Расчет невозможен', `${message}\n\n${steps}`);
}

const connectionSteps = '1. Проверьте подключение к серверу.\n2. При недоступности PostgreSQL или справочников обратитесь к администратору.\n3. Обновите страницу и повторите расчет.';
const inputSteps = '1. Выберите оба типа.\n2. Введите положительное целое количество и положительные параметры.\n3. Повторите расчет.';

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
    await showError(`Не удалось загрузить справочники: ${error.message}`, connectionSteps);
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
  if (button.disabled) return;
  if (!form.checkValidity()) {
    await showError('Заполните обязательные поля корректными числами.', inputSteps);
    form.querySelector(':invalid')?.focus();
    return;
  }

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
      await showError('Указаны неизвестные типы или некорректные параметры.', inputSteps);
      return;
    }
    showResult('success', `${result.material_requirement.toLocaleString('ru-RU')} ед.`, 'Материал с учетом брака; результат округлен вверх.');
  } catch (error) {
    await showError(`Не удалось рассчитать материал: ${error.message}`, connectionSteps);
  } finally {
    button.disabled = false;
  }
});

loadCatalogs();
