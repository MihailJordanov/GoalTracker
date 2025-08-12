(function () {
  const input = document.getElementById('searchInput');
  const table = document.getElementById('playersTable');
  if (!input || !table) return;

  const getRows = () => Array.from(table.querySelectorAll('tbody tr'));

  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();

    getRows().forEach(tr => {
      const nameEl = tr.querySelector('.name');
      const numberEl = tr.querySelector('.number');

      const nameText = nameEl ? nameEl.textContent.toLowerCase() : '';
      const numberText = numberEl ? numberEl.textContent.toLowerCase() : '';

      // Показва реда само ако името или номерът съдържат търсеното
      const match = nameText.includes(q) || numberText.includes(q);
      tr.style.display = match ? '' : 'none';
    });
  });
})();
