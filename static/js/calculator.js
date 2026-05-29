async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Request failed');
  }
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : response.text();
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0);
}

const zakatForm = document.getElementById('zakat-form');
const zakatResult = document.getElementById('zakat-result');

zakatForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(zakatForm).entries());
  try {
    const result = await apiFetch('/api/zakat/calculate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    zakatResult.innerHTML = `
      <h3>${result.nisab.is_above_nisab ? 'Zakat Due' : 'Below Nisab'}</h3>
      <p>Total assets: <strong>${formatCurrency(result.total_assets)}</strong></p>
      <p>Net assets: <strong>${formatCurrency(result.net_assets)}</strong></p>
      <p>Nisab threshold (${result.nisab.basis}): <strong>${formatCurrency(result.nisab.threshold)}</strong></p>
      <p>Zakat due: <strong>${formatCurrency(result.zakat_due)}</strong></p>
      <p>Gold price / gram: ${formatCurrency(result.prices.gold_per_gram)}</p>
      <p>Silver price / gram: ${formatCurrency(result.prices.silver_per_gram)}</p>
      <p>Next due date: <strong>${result.due_date || 'Not provided'}</strong></p>
    `;
  } catch (error) {
    zakatResult.textContent = `Unable to calculate Zakat: ${error.message}`;
  }
});

const charityList = document.getElementById('charity-list');
const charitySearch = document.getElementById('charity-search');
const charityCountry = document.getElementById('charity-country');
const charityCause = document.getElementById('charity-cause');
const loadCharitiesButton = document.getElementById('load-charities');

async function loadCharities() {
  charityList.innerHTML = 'Loading charity registry...';
  const params = new URLSearchParams({
    q: charitySearch.value,
    country: charityCountry.value,
    cause: charityCause.value,
  });
  try {
    const charities = await apiFetch(`/api/charities?${params.toString()}`);
    if (!charities.length) {
      charityList.innerHTML = '<p>No charities matched your filters.</p>';
      return;
    }
    charityList.innerHTML = charities.map((charity) => `
      <article class="charity-card">
        <h3>${charity.name}</h3>
        <div class="charity-meta">
          <span>${charity.country}</span>
          <span>${charity.cause}</span>
          <span>${charity.verification_source || 'manual'}</span>
          <span class="${charity.fraud_count > 0 ? 'status-warn' : 'status-ok'}">Fraud reports: ${charity.fraud_count}</span>
        </div>
        <p>Registration: ${charity.registration_number}</p>
        <p><a href="${charity.website}" target="_blank" rel="noreferrer">${charity.website}</a></p>
        <p>Last verified: ${charity.verified_at || 'Pending verification'}</p>
      </article>
    `).join('');
  } catch (error) {
    charityList.textContent = `Unable to load charities: ${error.message}`;
  }
}

loadCharitiesButton.addEventListener('click', loadCharities);
window.addEventListener('DOMContentLoaded', loadCharities);
