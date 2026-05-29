const reminderForm = document.getElementById('reminder-form');
const reminderOutput = document.getElementById('reminder-output');

reminderForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(reminderForm).entries());
  data.reminder_enabled = true;
  try {
    const result = await apiFetch('/api/reminders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    reminderOutput.innerHTML = `
      <p>Reminder saved for user #${result.id}</p>
      <pre>${JSON.stringify(result.schedule, null, 2)}</pre>
    `;
    reminderForm.reset();
  } catch (error) {
    reminderOutput.textContent = `Unable to save reminder: ${error.message}`;
  }
});
