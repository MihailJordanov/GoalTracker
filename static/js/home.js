document.addEventListener("DOMContentLoaded", function () {
    // Получаваме всички елементи с класа "dropdown-toggle"
    let dropdownButtons = document.querySelectorAll('.dropdown-toggle');
    
    dropdownButtons.forEach(function(button) {
        let menu = button.nextElementSibling;  // Следващият елемент е <ul class="dropdown-menu">

        // Скриваме менюто по подразбиране
        menu.style.display = 'none';

        // Обработваме клик върху бутон
        button.addEventListener('click', function(event) {
            event.preventDefault();  // Прекратяваме стандартното поведение на линка
            // Превключваме показването на менюто
            if (menu.style.display === 'block') {
                menu.style.display = 'none';
            } else {
                menu.style.display = 'block';
            }
        });

        // Скриваме менюто при клик извън него
        document.addEventListener('click', function(event) {
            if (!button.contains(event.target) && !menu.contains(event.target)) {
                menu.style.display = 'none';
            }
        });
    });
});

// Глобални функции за модала
function openModal() {
    var modal = document.getElementById('invite-modal');
    modal.classList.add('active');
    modal.querySelector('.close').style.display = 'block';  // Уверяваме се, че бутонът е видим
}

function closeModal() {
    var modal = document.getElementById('invite-modal');
    modal.classList.remove('active');
}


// Функция за автоматично преминаване на полетата
function moveToNextField(event, nextFieldId) {
    // Ако е въведен символ, преминаваме към следващото поле
    if (event.target.value.length === 1) {
        let nextField = document.getElementById(nextFieldId);
        if (nextField) nextField.focus(); // Ако следващото поле съществува, фокусираме върху него
    }
}

// Функция за връщане назад при натискане на Backspace
function moveToPreviousField(event, previousFieldId) {
    // Ако е натиснат Backspace и полето е празно
    if (event.key === "Backspace" && event.target.value === "") {
        document.getElementById(previousFieldId).focus();
    }
}


// Добавяне на обработчик за събития за backspace в полетата за ID
document.querySelectorAll('.player-id-field').forEach(function(inputField) {
    inputField.addEventListener('keydown', function(event) {
        moveToPreviousField(event, getPreviousFieldId(event.target.id));
    });
});

// Функция, която връща ID-то на предишното поле
function getPreviousFieldId(currentFieldId) {
    const fieldIds = [
        'player-id-1',
        'player-id-2',
        'player-id-3',
        'player-id-4',
        'player-id-5',
        'player-id-6'
    ];
    const currentIndex = fieldIds.indexOf(currentFieldId);
    return currentIndex > 0 ? fieldIds[currentIndex - 1] : null;
}

// Функция за движение със стрелките
function moveWithArrowKeys(event, currentFieldId) {
    const fieldIds = [
        'player-id-1',
        'player-id-2',
        'player-id-3',
        'player-id-4',
        'player-id-5',
        'player-id-6'
    ];

    const currentIndex = fieldIds.indexOf(currentFieldId);

    if (event.key === "ArrowRight" && currentIndex < fieldIds.length - 1) {
        document.getElementById(fieldIds[currentIndex + 1]).focus();
    } else if (event.key === "ArrowLeft" && currentIndex > 0) {
        document.getElementById(fieldIds[currentIndex - 1]).focus();
    }
}


function collectPlayerId() {
    // Събираме стойностите от всички полета
    let playerId = '';
    for (let i = 1; i <= 6; i++) {
        playerId += document.getElementById('player-id-' + i).value.toUpperCase();
    }

    // Поставяме комбинирания Player ID в скритото поле
    document.getElementById('combined-player-id').value = playerId;
}

// Добавяме обработка на изпращането на формата
document.getElementById('invite-form').addEventListener('submit', function(event) {
    collectPlayerId();  // Събираме стойността на Player ID преди изпращането
});


// Функция за отваряне на модала за покана на играч
function openInviteModal() {
    // Скриваме всички падащи менюта
    closeDropdowns();
    // Отваряме модала за покана на играч
    openModal();
}

// Функция за затваряне на всички падащи менюта
function closeDropdowns() {
    var dropdowns = document.querySelectorAll('.dropdown-menu');
    dropdowns.forEach(function(dropdown) {
        dropdown.style.display = 'none';  // Скриваме менюто
    });
}

// За да се затваря падащото меню при клик извън менюто, може да добавим и това:
window.addEventListener('click', function(event) {
    if (!event.target.closest('.dropdown')) {
        closeDropdowns();
    }
});

// Функция за отваряне на модала
function openModal() {
    document.getElementById('invite-modal').style.display = 'block';
}

// Функция за затваряне на модала
function closeModal() {
    document.getElementById('invite-modal').style.display = 'none';
}


document.getElementById('description').value = 'Hello champ! Would you like to join our team?';

    
