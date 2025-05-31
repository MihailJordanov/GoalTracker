window.addEventListener('DOMContentLoaded', () => {
  // lastname shrink
  const el = document.querySelector('.background-lastname');
  if (el) {
    const parentWidth = window.innerWidth * 0.9;
    let fontSize = 15;
    while (el.scrollWidth > parentWidth && fontSize > 8) {
      fontSize -= 1;
      el.style.fontSize = fontSize + 'vw';
    }
  }

  // number scaleX for mobile
  if (window.innerWidth <= 600) {
    const numberEl = document.querySelector('.background-number');
    if (numberEl) {
      const length = numberEl.textContent.trim().length;
      let scaleX = 1;
      if (length === 2) scaleX = 0.5;
      else if (length >= 3) scaleX = 0.4;

      numberEl.style.transform = `translate(-50%, -50%) scaleY(1.5) scale(5) scaleX(${scaleX})`;
    }
  }
});


window.addEventListener('load', () => {
    const loader = document.getElementById('page-loader');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => {
            loader.style.display = 'none';
        }, 500); // съвпада с CSS transition
    }
});
