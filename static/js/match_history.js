const toggleBtn = document.getElementById('toggleStatsBtn');
const statsContainer = document.getElementById('player-stats-container');

toggleBtn.addEventListener('click', () => {
    const isVisible = statsContainer.style.display === 'block';

    statsContainer.style.display = isVisible ? 'none' : 'block';
    toggleBtn.innerText = isVisible ? '▲ Show Player Statistics' : '▼ Hide Player Statistics';
});

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


function animateTitleCycle() {
    const spans = document.querySelectorAll('.reveal-title span');

    spans.forEach((span, i) => {
        // Reset styles
        span.style.opacity = 0;
        span.style.transform = 'scale(2)';
        span.style.animation = 'none';

        // Trigger reflow to reset animation
        void span.offsetWidth;

        // Delay per letter
        span.style.animation = `letterPop 0.6s forwards ease-out`;
        span.style.animationDelay = `${i * 0.05}s`;
    });

    // After 6s, fade them out with reverse animation
    setTimeout(() => {
        spans.forEach((span, i) => {
            span.style.animation = `letterFadeOut 0.4s forwards`;
            span.style.animationDelay = `${i * 0.03}s`;
        });
    }, 6000); // wait until initial animation completes
}

// Initial call
animateTitleCycle();

// Repeat every 10s
setInterval(animateTitleCycle, 7000);

window.addEventListener('load', () => {
    const loader = document.getElementById('page-loader');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => {
            loader.style.display = 'none';
        }, 500); // съвпада с CSS transition
    }
});

window.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash-messages');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease-out';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 2000); // скрий след 2 секунди
    });
});


document.addEventListener("DOMContentLoaded", function () {
    const cards = document.querySelectorAll('.match-card');
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    let currentIndex = 0;
    const step = 3;               // Колко мача да се виждат ==========================================================

    function showNextCards() {
        for (let i = currentIndex; i < currentIndex + step && i < cards.length; i++) {
            cards[i].style.display = 'block';
        }
        currentIndex += step;

        if (currentIndex >= cards.length) {
            loadMoreBtn.style.display = 'none';
        }
    }

    // Скрии всички карти и покажи първите 5
    cards.forEach(card => card.style.display = 'none');
    showNextCards();

    loadMoreBtn.addEventListener('click', showNextCards);
});


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
