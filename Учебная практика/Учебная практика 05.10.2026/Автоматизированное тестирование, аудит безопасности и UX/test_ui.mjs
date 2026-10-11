// Browser regression checks. CRUD requests are intercepted before reaching HTTP.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, existsSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';

const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = mkdtempSync('/private/tmp/final-audit-chrome-');
const chrome = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
let socket;
let passed = 0;
async function waitFor(check, message) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await check()) return;
    await delay(50);
  }
  throw new Error(`Timeout: ${message}`);
}
try {
  await waitFor(() => existsSync(`${profile}/DevToolsActivePort`), 'Chrome startup');
  const port = readFileSync(`${profile}/DevToolsActivePort`, 'utf8').split('\n')[0];
  const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
  socket = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  socket.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (!message.id) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(JSON.stringify(message.error)));
    else resolve(message.result);
  };
  const cdp = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  await cdp('Page.enable');
  let injectionId;
  async function open(path, mode = '') {
    if (injectionId) await cdp('Page.removeScriptToEvaluateOnNewDocument', { identifier: injectionId });
    const source = `
      window.__auditMode = ${JSON.stringify(mode)};
      const originalFetch = window.fetch.bind(window);
      window.fetch = (url, options = {}) => {
        const method = (options.method || 'GET').toUpperCase();
        if (method !== 'GET' && url !== '/api/material/calculate') {
          window.__saveCount = (window.__saveCount || 0) + 1;
          return new Promise(resolve => { window.__resolveSave = resolve; });
        }
        if (window.__auditMode === 'catalogError' && url === '/api/material/catalogs')
          return Promise.resolve(new Response(JSON.stringify({error:'PostgreSQL недоступен'}), {status:503}));
        if (window.__auditMode === 'listError' && url === '/api/partners')
          return Promise.reject(new Error('Нет соединения'));
        if (window.__auditMode === 'emptyHistory' && url.endsWith('/history'))
          return Promise.resolve(new Response(JSON.stringify({partner:{id:1,company_name:'Тест'},rows:[]})));
        if (window.__auditMode === 'delayPartner' && url === '/api/partners/1')
          return new Promise(resolve => { window.__resolvePartner = resolve; });
        return originalFetch(url, options);
      };`;
    injectionId = (await cdp('Page.addScriptToEvaluateOnNewDocument', { source })).identifier;
    await cdp('Page.navigate', { url: `http://127.0.0.1:8010/${path}` });
    await waitFor(async () => {
      try { return await evaluate(`location.href.endsWith(${JSON.stringify(path)}) && document.readyState === 'complete'`); }
      catch { return false; }
    }, path);
  }
  async function ready(expression) { await waitFor(() => evaluate(expression), expression); }
  async function closeDialog() { await evaluate("document.querySelector('#dialogActions button').click()"); }
  function done(name) { passed++; console.log(`PASS ${name}`); }

  await open('index.html');
  await ready("document.querySelectorAll('.partner-row').length > 0");
  assert(await evaluate("document.querySelector('.partner-row').textContent.includes('Рейтинг:')"));
  const id = await evaluate("document.querySelector('input[name=selectedPartner]').value");
  await evaluate("document.querySelector('input[name=selectedPartner]').click(); document.querySelector('#historyButton').click()");
  await ready("location.pathname.endsWith('history.html') && !document.querySelector('#partnerSummary')?.hidden");
  assert(await evaluate(`[...document.querySelectorAll('.back-to-register')].length === 2 && [...document.querySelectorAll('.back-to-register')].every(a => a.href.endsWith('index.html?selected=${id}'))`));
  await evaluate("document.querySelector('.back-to-register').click()");
  await ready(`document.querySelector('input[name=selectedPartner]:checked')?.value === '${id}'`);
  done('real partner list, rating, history and selected return');

  await open('calculator.html');
  await ready("!document.querySelector('#calculateButton').disabled");
  await evaluate(`Object.entries({product_type_id:'1',material_type_id:'2',quantity:'100',param_1:'1',param_2:'1'}).forEach(([key,value]) => document.forms.calculatorForm.elements[key].value=value); document.forms.calculatorForm.requestSubmit()`);
  await ready("document.querySelector('#resultValue').textContent.includes('126')");
  await evaluate("document.forms.calculatorForm.elements.param_1.value='-1'; document.forms.calculatorForm.requestSubmit()");
  await ready("document.querySelector('#messageDialog').open");
  assert(await evaluate("document.querySelector('#dialogIcon').textContent === '×' && document.querySelector('#dialogMessage').textContent.includes('1.')"));
  await closeDialog();
  await evaluate("document.forms.calculatorForm.elements.param_1.value=''; document.forms.calculatorForm.requestSubmit()");
  await ready("document.querySelector('#messageDialog').open");
  await closeDialog();
  done('real catalogs and 126 calculation; invalid and missing input dialogs');

  await open('calculator.html', 'catalogError');
  await ready("document.querySelector('#messageDialog').open");
  assert(await evaluate("document.querySelector('#calculateButton').disabled && document.querySelector('#dialogMessage').textContent.includes('PostgreSQL')"));
  await closeDialog();
  done('catalog outage dialog and disabled calculation');

  await open('history.html?partner_id=2147483647');
  await ready("document.querySelector('#messageDialog').open");
  assert(await evaluate("document.querySelector('#dialogIcon').textContent === '×' && document.querySelector('#historyTableWrap').hidden"));
  await closeDialog();
  await open('history.html?partner_id=1', 'emptyHistory');
  await ready("document.querySelector('#historyMessage').textContent.includes('пока нет')");
  assert(await evaluate("!document.querySelector('#messageDialog').open && document.querySelector('#historyTableWrap').hidden"));
  done('missing partner error; empty history');

  await open('index.html?saved=1', 'listError');
  await ready("document.querySelector('#messageDialog').open");
  await closeDialog();
  await delay(100);
  assert(await evaluate("!document.querySelector('#messageDialog').open && document.querySelector('#partnerCount').textContent === 'Ошибка загрузки'"));
  done('failed list reload does not report success');

  await open('partner-edit.html?mode=create');
  await ready("!document.querySelector('#saveButton').disabled");
  const fill = `Object.entries({company_name:'Тест аудита',partner_type:'ООО',inn:'1234567890',email:'audit@example.test',rating:'0'}).forEach(([key,value])=>document.forms.partnerForm.elements[key].value=value)`;
  await evaluate(`${fill}; document.forms.partnerForm.requestSubmit()`);
  await ready("Boolean(window.__resolveSave)");
  assert(await evaluate("document.forms.partnerForm.inert && document.querySelector('#saveButton').disabled"));
  assert(await evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});window.dispatchEvent(e);return e.defaultPrevented})()"));
  await evaluate("document.forms.partnerForm.requestSubmit()");
  assert.equal(await evaluate('window.__saveCount'), 1);
  await evaluate("window.__resolveSave(new Response(JSON.stringify({error:'Ошибка соединения'}),{status:500}))");
  await ready("document.querySelector('#messageDialog').open");
  assert(await evaluate("!document.forms.partnerForm.inert && document.forms.partnerForm.elements.company_name.value === 'Тест аудита'"));
  await closeDialog();
  await evaluate("document.querySelector('#cancelButton').click()");
  await ready("document.querySelector('#messageDialog').open");
  await closeDialog();
  assert(await evaluate("location.pathname.endsWith('partner-edit.html')"));
  await evaluate("document.querySelector('#cancelButton').click()");
  await ready("document.querySelector('#messageDialog').open");
  await evaluate("document.querySelector('#dialogActions button:last-child').click()");
  await ready("location.pathname.endsWith('index.html')");
  done('pending save guard, unload warning, duplicate submit, preserved input and cancel/stay/leave');

  await open('partner-edit.html?mode=edit&partner_id=1', 'delayPartner');
  await ready('Boolean(window.__resolvePartner)');
  assert(await evaluate("document.querySelector('#saveButton').disabled"));
  await evaluate('document.forms.partnerForm.requestSubmit()');
  assert.equal(await evaluate('window.__saveCount || 0'), 0);
  await evaluate(`window.__resolvePartner(new Response(JSON.stringify({id:1, company_name:'Исходный',partner_type:'ООО',inn:'1234567890',email:'audit@example.test',rating:0})))`);
  await ready("!document.querySelector('#saveButton').disabled");
  await evaluate(`${fill}; document.forms.partnerForm.requestSubmit()`);
  await ready('Boolean(window.__resolveSave)');
  await evaluate("window.__resolveSave(new Response(JSON.stringify({id:1}),{status:200}))");
  await ready("location.pathname.endsWith('index.html') && document.querySelector('#messageDialog')?.open");
  assert(await evaluate("document.querySelector('#dialogTitle').textContent === 'Изменения сохранены'"));
  await closeDialog();
  done('save blocked before load; successful mocked edit redirects without unsaved warning');
  console.log(`${passed} browser scenarios passed. No CRUD request reached PostgreSQL.`);
} finally {
  socket?.close();
  chrome.kill('SIGTERM');
}
