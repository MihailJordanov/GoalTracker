window.onload = function() {
    const flashMessages = document.querySelectorAll('.flash-message');

    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.animation = 'fadeOut 1s forwards';

            // Премахваме от DOM след края на анимацията (по желание)
            setTimeout(function() {
                message.remove();
            }, 1000); // 1 секунда = продължителността на fadeOut
        }, 2000); // Показва се 2 секунди
    });
};
