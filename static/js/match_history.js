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




