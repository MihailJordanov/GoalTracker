// === Player stats toggle ===
const toggleBtn = document.getElementById('toggleStatsBtn');
const statsContainer = document.getElementById('player-stats-container');

if (toggleBtn && statsContainer) {
  toggleBtn.addEventListener('click', () => {
    const isVisible = statsContainer.style.display === 'block';
    statsContainer.style.display = isVisible ? 'none' : 'block';
    toggleBtn.innerText = isVisible ? '▲ Show Player Statistics' : '▼ Hide Player Statistics';
  });
}

// === Load player stats on match click ===
document.querySelectorAll('.match-card.clickable').forEach(row => {
  row.addEventListener('click', () => {
    const matchId = row.getAttribute('data-match-id');
    fetch(`/match/${matchId}/players`)
      .then(res => res.text())
      .then(html => {
        statsContainer.innerHTML = html;
        statsContainer.style.display = 'block';
        toggleBtn.style.display = 'block';
        toggleBtn.innerText = '▲ Hide Player Statistics';
      });
  });
});

// === Reveal title animation ===
function animateTitleCycle() {
  const spans = document.querySelectorAll('.reveal-title span');

  spans.forEach((span, i) => {
    // Reset styles
    span.style.opacity = 0;
    span.style.transform = 'scale(2)';
    span.style.animation = 'none';
    // Trigger reflow
    void span.offsetWidth;
    // In
    span.style.animation = `letterPop 0.6s forwards ease-out`;
    span.style.animationDelay = `${i * 0.05}s`;
  });

  // Fade out
  setTimeout(() => {
    spans.forEach((span, i) => {
      span.style.animation = `letterFadeOut 0.4s forwards`;
      span.style.animationDelay = `${i * 0.03}s`;
    });
  }, 6000);
}
animateTitleCycle();
setInterval(animateTitleCycle, 7000);

// === Loader fade-out ===
window.addEventListener('load', () => {
  const loader = document.getElementById('page-loader');
  if (loader) {
    loader.style.opacity = '0';
    setTimeout(() => {
      loader.style.display = 'none';
    }, 500);
  }
});

// === Flash messages auto-hide ===
window.addEventListener('DOMContentLoaded', () => {
  const flashMessages = document.querySelectorAll('.flash-messages');
  flashMessages.forEach(msg => {
    setTimeout(() => {
      msg.style.transition = 'opacity 0.5s ease-out';
      msg.style.opacity = '0';
      setTimeout(() => msg.remove(), 500);
    }, 2000);
  });
});

// === VIEW MODE & PAGINATION (Detailed / Compact) ===
document.addEventListener('DOMContentLoaded', function () {
  const cardsContainer = document.getElementById('matchCards');
  const cards = Array.from(document.querySelectorAll('.match-card'));
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const toggleWrap = document.getElementById('viewToggle');
  const detailedBtn = toggleWrap?.querySelector('[data-mode="detailed"]');
  const compactBtn = toggleWrap?.querySelector('[data-mode="compact"]');

  const STEP_DETAILED = 5;   // по подразбиране
  const STEP_COMPACT  = 15;  // compact – съвпада с интро лимита

  let mode = 'detailed';
  let currentIndex = 0;

  // helper: compact intro animation
  function addResultFlashIcon(card, delayMs = 0) {
    // избери иконата според класа win/loss/draw
    let iconClass = 'fa-trophy';     // по подразбиране (win)
    if (card.classList.contains('loss')) iconClass = 'fa-skull';
    else if (card.classList.contains('draw')) iconClass = 'fa-handshake';

    const icon = document.createElement('i');
    icon.className = `flash-icon fa-solid ${iconClass}`;

    // синхронизираме старта с card-анимацията
    icon.style.animationDelay = `${delayMs}ms`; 

    // поставяме я вътре в картата
    card.style.position = card.style.position || 'relative';
    card.appendChild(icon);

    // почиства се автоматично след края на анимацията
    icon.addEventListener('animationend', () => icon.remove());
  }



  function runCompactIntro(targetCards, limit = 15, baseDelay = 70) {
    // уважаваме системната настройка за намалена анимация
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    const n = Math.min(limit, targetCards.length);
    for (let i = 0; i < n; i++) {
      const card = targetCards[i];
      if (getComputedStyle(card).display === 'none') continue;

      // reset
      card.classList.remove('compact-intro');
      card.style.animationDelay = '0ms';

      const delay = i * baseDelay;
      // за 2-те анимации (spin + flash)
      card.style.animationDelay = `${delay}ms, ${delay}ms`;
      card.classList.add('compact-intro');

      addResultFlashIcon(card, delay);


      // cleanup след края на flash
      const cleanup = (e) => {
        if (e.animationName === 'compactFlash') {
          card.classList.remove('compact-intro');
          card.style.animationDelay = '';
          card.removeEventListener('animationend', cleanup);
        }
      };
      card.addEventListener('animationend', cleanup);
    }
  }

  // показва поредната „страница“; връща масив с ново-показаните карти
  function showNextCards() {
    const start = currentIndex;
    const step = (mode === 'compact') ? STEP_COMPACT : STEP_DETAILED;
    const end = Math.min(currentIndex + step, cards.length);

    for (let i = start; i < end; i++) {
      cards[i].style.display = 'block';
    }
    currentIndex = end;

    if (loadMoreBtn) {
      loadMoreBtn.style.display = (currentIndex >= cards.length) ? 'none' : 'inline-block';
    }

    return cards.slice(start, end);
  }

  // прилагане на режим + ресет на странирането
  function applyModeBase(newMode) {
    mode = newMode;

    // Toggle active button UI
    if (detailedBtn && compactBtn) {
      detailedBtn.classList.toggle('active', mode === 'detailed');
      compactBtn.classList.toggle('active', mode === 'compact');
      detailedBtn.setAttribute('aria-selected', mode === 'detailed' ? 'true' : 'false');
      compactBtn.setAttribute('aria-selected', mode === 'compact' ? 'true' : 'false');
    }

    // Toggle CSS class on container for styling
    const container = document.querySelector('.container');
    if (container) {
      container.classList.toggle('compact-mode', mode === 'compact');
    }

    // Reset pagination display
    currentIndex = 0;
    cards.forEach(card => (card.style.display = 'none'));
    const firstBatch = showNextCards();

    // compact интро при превключване
    if (mode === 'compact') {
      runCompactIntro(firstBatch, Math.min(15, firstBatch.length), 70);
    }
  }

  // обвивка, която също движи плъзгача и ARIA
  let applyMode = function (newMode) {
    applyModeBase(newMode);
    const viewToggle = document.getElementById('viewToggle');
    if (viewToggle) viewToggle.classList.toggle('compact-active', newMode === 'compact');
  };

  // Initial render
  cards.forEach(card => (card.style.display = 'none'));
  const initialBatch = showNextCards();

  // синхронизирай плъзгача на старта (ако някой ден стартираш в compact)
  const viewToggleEl = document.getElementById('viewToggle');
  if (viewToggleEl) viewToggleEl.classList.toggle('compact-active', mode === 'compact');

  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => {
      const newlyShown = showNextCards();
      // ако сме в compact – анимираме новите карти с по-кратък delay
      if (mode === 'compact' && newlyShown.length) {
        runCompactIntro(newlyShown, newlyShown.length, 40);
      }
    });
  }

  // === Toggle handling — act as a single switch (any click toggles) ===
  if (toggleWrap) {
    // плавен fade/slide на контейнера при смяна
    function animateContentSwitch(cb) {
      if (!cardsContainer) { cb(); return; }
      cardsContainer.classList.add('switching-out');
      setTimeout(() => {
        cb(); // applyMode(...)
        cardsContainer.classList.remove('switching-out');
        cardsContainer.classList.add('switching-in');
        setTimeout(() => cardsContainer.classList.remove('switching-in'), 220);
      }, 180);
    }

    // клик навсякъде върху превключвателя => toggle
    toggleWrap.addEventListener('click', () => {
      const next = (mode === 'detailed') ? 'compact' : 'detailed';
      animateContentSwitch(() => applyMode(next));
    });

    // достъпност: Space/Enter също превключват (оставяме role=tablist от HTML)
    toggleWrap.tabIndex = 0;

    toggleWrap.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        const next = (mode === 'detailed') ? 'compact' : 'detailed';
        animateContentSwitch(() => applyMode(next));
      }
    });
  }
});

// === MOBILE tooltip for player rows (click entire row) ===
(function () {
  const mq = window.matchMedia('(max-width: 600px)');
  let currentTooltip = null;
  let currentRowEl = null;

  function removeTooltip() {
    if (currentTooltip) {
      currentTooltip.remove();
      currentTooltip = null;
    }
    if (currentRowEl) {
      currentRowEl.classList.remove('active');
      currentRowEl = null;
    }
  }

  function showTooltip(row) {
    removeTooltip();

    const name = row.dataset.playerName?.trim() || 'Unknown';
    const tip = document.createElement('div');
    tip.className = 'player-tooltip';
    tip.textContent = name;
    document.body.appendChild(tip);

    const r = row.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();

    let top = r.top - tipRect.height - 8;
    let arrowDirection = 'up';
    if (top < 8) {
      top = r.bottom + 8;
      arrowDirection = 'down';
    }

    let left = r.left + (r.width / 2) - (tipRect.width / 2);
    left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));

    tip.style.top = top + 'px';
    tip.style.left = left + 'px';

    const arrowX = r.left + (r.width / 2) - left;
    tip.style.setProperty('--arrow-x', arrowX + 'px');
    tip.dataset.arrowDirection = arrowDirection;

    row.classList.add('active');
    currentTooltip = tip;
    currentRowEl = row;
  }

  document.addEventListener('click', function (e) {
    if (!mq.matches) return;

    const target = e.target.closest('.player-row');
    if (target) {
      if (target.classList.contains('active')) {
        removeTooltip();
      } else {
        showTooltip(target);
      }
    } else {
      removeTooltip();
    }
  });

  window.addEventListener('resize', () => {
    if (!mq.matches) removeTooltip();
  });

  window.addEventListener('scroll', () => {
    if (mq.matches) removeTooltip();
  }, { passive: true });
})();
