(function () {
  const btn = document.getElementById('sortToggle');
  const list = document.getElementById('playersList');
  if (!btn || !list) return;

  const byNumber = (a, b) => {
    const an = parseInt(a.dataset.number) || Number.POSITIVE_INFINITY;
    const bn = parseInt(b.dataset.number) || Number.POSITIVE_INFINITY;
    if (an !== bn) return an - bn;
    const al = a.dataset.last, bl = b.dataset.last;
    if (al !== bl) return al.localeCompare(bl);
    return a.dataset.first.localeCompare(b.dataset.first);
  };

  const byWinRateDesc = (a, b) => {
    const aw = parseFloat(a.dataset.winrate);
    const bw = parseFloat(b.dataset.winrate);
    if (bw !== aw) return bw - aw;  // higher first
    return byNumber(a, b);          // tie-breaker
  };

  btn.addEventListener('click', () => {
    const items = Array.from(list.querySelectorAll('.player'));
    const mode = btn.getAttribute('data-mode') || 'number';

    if (mode === 'number') {
      items.sort(byWinRateDesc);
      btn.textContent = 'Sort by number';
      btn.setAttribute('data-mode', 'winrate');
    } else {
      items.sort(byNumber);
      btn.textContent = 'Sort by win rate';
      btn.setAttribute('data-mode', 'number');
    }

    items.forEach(el => list.appendChild(el));
  });
})();
