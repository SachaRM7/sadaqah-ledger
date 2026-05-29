const ledgerForm = document.getElementById('ledger-form');
const ledgerOutput = document.getElementById('ledger-output');
const verifyLedgerButton = document.getElementById('verify-ledger');

ledgerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(ledgerForm).entries());
  try {
    const result = await apiFetch('/api/donations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    ledgerOutput.textContent = JSON.stringify(result, null, 2);
    ledgerForm.reset();
    await verifyLedger();
  } catch (error) {
    ledgerOutput.textContent = `Unable to record donation: ${error.message}`;
  }
});

async function verifyLedger() {
  try {
    const result = await apiFetch('/api/ledger');
    ledgerOutput.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    ledgerOutput.textContent = `Ledger verification failed: ${error.message}`;
  }
}

verifyLedgerButton.addEventListener('click', verifyLedger);
window.addEventListener('DOMContentLoaded', verifyLedger);
