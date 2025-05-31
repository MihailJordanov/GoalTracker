document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("editMatchForm");

    if (!form) return;

    form.addEventListener("submit", function (event) {
        const checkboxes = form.querySelectorAll('input[name="played[]"]');
        const homeResult = parseInt(form.querySelector('input[name="home_team_result"]').value);
        const awayResult = parseInt(form.querySelector('input[name="away_team_result"]').value);

        let isChecked = false;
        let totalGoals = 0;
        let totalAssists = 0;
        let errorMessage = "";

        // Запълване с 0 ако поле е празно
        const numberInputs = form.querySelectorAll('input[type="number"]');
        numberInputs.forEach(input => {
            if (input.value.trim() === '') {
                input.value = 0;
            }
        });

        // Проверка дали има маркиран играч
        checkboxes.forEach(cb => {
            if (cb.checked) isChecked = true;
        });

        if (!isChecked) {
            alert("Please select at least one player as having played.");
            event.preventDefault();
            return;
        }

        // Проверка за отрицателни стойности
        for (const input of numberInputs) {
            const value = parseInt(input.value);
            if (value < 0) {
                alert("No field can have a negative value.");
                event.preventDefault();
                return;
            }
        }

        // Събиране на статистики
        const playerStats = {};

        for (const el of form.elements) {
            if (el.name.startsWith("player_")) {
                const [_, stat, uid] = el.name.split("_");
                const value = parseInt(el.value) || 0;

                if (!playerStats[uid]) playerStats[uid] = {};
                playerStats[uid][stat] = value;
            }
        }

        // Проверки за логика
        for (const uid in playerStats) {
            const stats = playerStats[uid];

            const goals = stats.goals || 0;
            const assists = stats.assists || 0;
            const shoots = stats.shoots || 0;
            const shoots_on_target = stats.shoots_on_target || 0;
            const yellow = stats.yellow_cards || 0;
            const red = stats.red_cards || 0;

            totalGoals += goals;
            totalAssists += assists;

            if ((goals + assists) > homeResult) {
                errorMessage = `Total goals + assists for player #${uid} exceeds home result.`;
                break;
            }

            if (yellow > 2) {
                errorMessage = `Player #${uid} has more than 2 yellow cards.`;
                break;
            }

            if (red > 1) {
                errorMessage = `Player #${uid} has more than 1 red card.`;
                break;
            }

            if (shoots < shoots_on_target) {
                errorMessage = `Player #${uid} has more shots on target than total shots.`;
                break;
            }
        }

        if (!errorMessage && totalGoals > homeResult) {
            errorMessage = "Total team goals exceed home result.";
        }

        if (!errorMessage && totalAssists > homeResult) {
            errorMessage = "Total team assists exceed home result.";
        }

        if (errorMessage) {
            alert(errorMessage);
            event.preventDefault();
        }

        // Валидация за дузпи, ако са активирани
        const penaltyCheckbox = document.getElementById("penalty_checkbox");
        if (penaltyCheckbox && penaltyCheckbox.checked) {
            const homePen = parseInt(form.querySelector('input[name="home_team_penalty"]').value) || 0;
            const awayPen = parseInt(form.querySelector('input[name="away_team_penalty"]').value) || 0;

            if (homePen === awayPen) {
                alert("Penalty shootout result cannot be a draw.");
                event.preventDefault();
                return;
            }
        }

        // Ако чекбоксът за дузпи не е отметнат, нулирай стойностите
        if (penaltyCheckbox && !penaltyCheckbox.checked) {
            const homePenInput = form.querySelector('input[name="home_team_penalty"]');
            const awayPenInput = form.querySelector('input[name="away_team_penalty"]');
            if (homePenInput) homePenInput.value = 0;
            if (awayPenInput) awayPenInput.value = 0;
        }

    }); 

    // Tooltip при клик върху иконка (cell-label)
    document.querySelectorAll('.cell-label').forEach(label => {
        label.addEventListener('click', () => {
            const isActive = label.classList.contains('active');

            // Скриване на всички активни (ако показваме само един едновременно)
            document.querySelectorAll('.cell-label.active').forEach(el => {
                el.classList.remove('active');
            });

            // Ако вече е активна – не я отваря пак
            if (!isActive) {
                label.classList.add('active');

                // Автоматично скриване след 2 секунди
                setTimeout(() => {
                    label.classList.remove('active');
                }, 2000);
            }
        });
    });
});


document.getElementById('deleteMatchBtn').addEventListener('click', function () {
    Swal.fire({
        title: 'Delete this match?',
        text: "This action cannot be undone!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!',
        reverseButtons: true
    }).then((result) => {
        if (result.isConfirmed) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = deleteMatchUrl;  // <-- използваме предварително подадения URL
            document.body.appendChild(form);
            form.submit();
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const homeInput = document.querySelector('input[name="home_team_result"]');
    const awayInput = document.querySelector('input[name="away_team_result"]');
    const checkbox = document.getElementById('penalty_checkbox');
    const penaltyFields = document.getElementById('penalty_fields');

    function updatePenaltyCheckboxState() {
        const homeVal = parseInt(homeInput.value);
        const awayVal = parseInt(awayInput.value);

        if (homeVal === awayVal) {
            checkbox.disabled = false;
        } else {
            checkbox.disabled = true;
            checkbox.checked = false;
            penaltyFields.style.display = 'none';
        }
    }

    checkbox.addEventListener('change', () => {
        penaltyFields.style.display = checkbox.checked ? 'block' : 'none';
    });

    homeInput.addEventListener('input', updatePenaltyCheckboxState);
    awayInput.addEventListener('input', updatePenaltyCheckboxState);

    updatePenaltyCheckboxState(); // initial call
});





