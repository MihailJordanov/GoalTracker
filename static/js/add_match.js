document.addEventListener('DOMContentLoaded', function() {
    var container = document.querySelector('.user-stats');
    var teamOneResultInput = document.getElementById('team_one_result');
    var matchForm = document.getElementById('match-form');
    var awayTeamSelect = document.getElementById('team_two');
    var locationSelect = document.getElementById('location');

    // Извличане на отбори
    fetch('/getTeams')
        .then(response => response.json())
        .then(teams => {
            teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.id; // ✅ Това ще се изпрати във формата
                option.textContent = `${team.name}` ;
                awayTeamSelect.appendChild(option);
            });
        })

        .catch(error => {
            console.error('Error fetching teams:', error);
            alert('Error loading teams.');
        });

    // Извличане на локации
    fetch('/getLocations')
        .then(response => response.json())
        .then(locations => {
            const locationSelect = document.getElementById('location');
            locationSelect.innerHTML = '<option value="" disabled selected>Select a Location</option>';

            locations.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc.id;
                option.textContent = loc.name;
                locationSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error fetching locations:', error);
        });

    // Извличане на потребителите и динамично създаване на формата за статистики
    fetch('/getUsers')
        .then(response => response.json())
        .then(users => {
            users.forEach(user => {
                if (user.type >= 1) {
                    var userSection = document.createElement('div');
                    userSection.classList.add('user-section');

                    userSection.innerHTML = `
                        <h3>${user.last_name}</h3>  
                        <label class="played-label">
                            <input type="checkbox" name="played_${user.id}" class="played-checkbox" data-user-id="${user.id}" checked>
                            Played
                        </label>
                        <div class="stats-fields">
                            <label for="goals_${user.id}">Goals:</label>
                            <input type="number" id="goals_${user.id}" name="goals_${user.id}" class="stats-field" value="0" min="0">
                            <label for="assists_${user.id}">Assists:</label>
                            <input type="number" id="assists_${user.id}" name="assists_${user.id}" class="stats-field" value="0" min="0">

                            <div class="extra-stats" style="display: none; margin-top: 10px;">
                                <label for="shots_${user.id}">Shoots:</label>
                                <input type="number" id="shots_${user.id}" name="shots_${user.id}" class="stats-field" value="0" min="0">
                                <label for="shots_on_target_${user.id}">Shoots on Target:</label>
                                <input type="number" id="shots_on_target_${user.id}" name="shots_on_target_${user.id}" class="stats-field" value="0" min="0">
                                <label for="blocked_shoots_${user.id}">Blocked Shoots:</label>
                                <input type="number" id="blocked_shoots_${user.id}" name="blocked_shoots_${user.id}" class="stats-field" value="0" min="0">
                                <label for="saved_goals_${user.id}">Saved Shoots:</label>
                                <input type="number" id="saved_goals_${user.id}" name="saved_goals_${user.id}" class="stats-field" value="0" min="0">
                                <label for="passes_${user.id}">Passes:</label>
                                <input type="number" id="passes_${user.id}" name="passes_${user.id}" class="stats-field" value="25" min="0">
                                <label for="fouls_${user.id}">Fouls:</label>
                                <input type="number" id="fouls_${user.id}" name="fouls_${user.id}" class="stats-field" value="0" min="0">
                                <label for="yellow_cards_${user.id}">Yellow Cards:</label>
                                <input type="number" id="yellow_cards_${user.id}" name="yellow_cards_${user.id}" class="stats-field" value="0" min="0" max="2">
                                <label for="red_cards_${user.id}">Red Cards:</label>
                                <input type="number" id="red_cards_${user.id}" name="red_cards_${user.id}" class="stats-field" value="0" min="0" max="1">
                            </div>
                            <button type="button" class="toggle-extra-stats">Show more</button>
                        </div>
                    `;


                
                container.appendChild(userSection);

                // 🔽 Тук добавяш логиката за показване/скриване на статистиките
                const checkbox = userSection.querySelector('.played-checkbox');
                const statsFields = userSection.querySelector('.stats-fields');
                
                function toggleStatsFields() {
                    if (checkbox.checked) {
                        statsFields.style.maxHeight = null;
                        userSection.classList.remove('inactive');
                    } else {
                        userSection.classList.add('inactive');
                    }
                }

                // 🔽 Toggle за "Show more"
                const toggleButton = userSection.querySelector('.toggle-extra-stats');
                const extraStats = userSection.querySelector('.extra-stats');

                toggleButton.addEventListener('click', () => {
                    const isHidden = extraStats.style.display === 'none';
                    extraStats.style.display = isHidden ? 'block' : 'none';
                    toggleButton.textContent = isHidden ? 'Hide extra stats' : 'Show more';
                });


                
                toggleStatsFields();
                checkbox.addEventListener('change', toggleStatsFields);
                
                }
            });
            

        })
        .catch(error => {
            console.error('Error fetching users:', error);
            alert('Error loading users.');
        });

        // Валидация преди изпращане на формата
        matchForm.addEventListener('submit', function(event) {


            function showFieldError(inputElement, message) {
                inputElement.classList.add('field-error');
            
                // премахни съобщение ако вече има
                const existingMsg = inputElement.parentElement.querySelector('.field-error-message');
                if (existingMsg) existingMsg.remove();
            
                const msg = document.createElement('div');
                msg.className = 'field-error-message';
                msg.textContent = message;
                inputElement.parentElement.appendChild(msg);
            
                inputElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                inputElement.focus();
            }
            

            // Премахни стари грешки
            document.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
            document.querySelectorAll('.field-error-message').forEach(el => el.remove());

            // Проверки за празни задължителни полета
            const requiredFields = [
                { id: 'schema', message: 'Please enter a tactical schema (e.g. 4-4-2)' },
                { id: 'format', message: 'Please select a valid match format' },
                { id: 'team_one', message: 'Please enter the home team' },
                { id: 'team_two', message: 'Please select the away team' },
                { id: 'location', message: 'Please select a location' },
                { id: 'date', message: 'Please pick a match date' },
                { id: 'team_one_result', message: 'Please enter the result for the home team' },
                { id: 'team_two_result', message: 'Please enter the result for the away team' },
            ];

            for (let field of requiredFields) {
                const el = document.getElementById(field.id);
                if (!el.value.trim()) {
                    event.preventDefault();
                    showFieldError(el, field.message);
                    return;
                }
            }


            // ✅ Първо: Попълване на празни полета с 0
            document.querySelectorAll('.stats-field').forEach(input => {
                if (input.value.trim() === '') {
                    input.value = 0;
                }
            });
        
            // ✅ След това: Tactical schema vs format validation
            const schema = document.getElementById("schema").value.trim();
            const format = parseInt(document.getElementById("format").value);
        
            const parts = schema.split("-").map(num => parseInt(num));
            if (schema !== "" && parts.some(isNaN)) {
                event.preventDefault();
                showFieldError(document.getElementById('schema'), "Invalid tactical schema format. Use only numbers separated by dashes (e.g. 4-3-3).");
                return;
            }
        
            const sum = parts.reduce((acc, val) => acc + val, 0);
            if (sum > format) {
                event.preventDefault();
                showFieldError(document.getElementById('schema'), `The total number of players in the tactical schema (${sum}) exceeds the match format (${format}v${format}).`);
                return;
            }
        
            // ✅ Проверка: поне един играч трябва да е отбелязан като "Played"
            const playedCheckboxes = document.querySelectorAll('.played-checkbox:checked');

            if (playedCheckboxes.length === 0) {
                event.preventDefault();
                showFieldError(document.querySelector('.played-checkbox'), "At least one player must be marked as 'Played'.");
                return;
            }

            // ✅ И сега валидацията за головете
            let totalGoals = 0;
            document.querySelectorAll('.played-checkbox:checked').forEach(checkbox => {
                let userId = checkbox.getAttribute('data-user-id');
                let goals = parseInt(document.getElementById(`goals_${userId}`).value) || 0;
                totalGoals += goals;
            });
        
            let teamOneResult = parseInt(teamOneResultInput.value) || 0;
            if (totalGoals > teamOneResult) {
                event.preventDefault();
                showFieldError(document.getElementById('team_one_result'), "The total number of player goals cannot exceed the home team's result.");
                return
            }

            // ✅ Валидация: Асистенции <= резултат
            let totalAssists = 0;
            document.querySelectorAll('.played-checkbox:checked').forEach(checkbox => {
                let userId = checkbox.getAttribute('data-user-id');
                let assists = parseInt(document.getElementById(`assists_${userId}`).value) || 0;
                totalAssists += assists;
            });

            if (totalAssists > teamOneResult) {
                event.preventDefault();
                showFieldError(document.getElementById('team_one_result'), "Total assists cannot exceed home team result.");
                return
            }

            // 🔽 Валидация: ако има дузпи – стойностите не трябва да са равни
            if (penaltyCheckbox.checked) {
                const homePenalty = parseInt(document.getElementById('home_team_penalty').value) || 0;
                const awayPenalty = parseInt(document.getElementById('away_team_penalty').value) || 0;

                if (homePenalty === awayPenalty) {
                    event.preventDefault();
                    showFieldError(document.getElementById('home_team_penalty'), "Penalty shootout cannot end in a draw. Please adjust the score.");
                    return;
                }
            }
        });    

        const penaltyCheckbox = document.getElementById('penalty_checkbox');
        const penaltyFields = document.getElementById('penalty_fields');
        const teamOneInput = document.getElementById('team_one_result');
        const teamTwoInput = document.getElementById('team_two_result');
        const penaltyLabel = document.getElementById('penalty_label');

        function checkForDrawAndTogglePenalties() {
            const homeGoals = parseInt(teamOneInput.value) || 0;
            const awayGoals = parseInt(teamTwoInput.value) || 0;

            if (homeGoals === awayGoals) {
                penaltyCheckbox.disabled = false;
                penaltyLabel.style.opacity = '1';
            } else {
                penaltyCheckbox.checked = false;
                penaltyCheckbox.disabled = true;
                penaltyLabel.style.opacity = '0.5';
                penaltyFields.style.display = 'none';
            }
        }

        teamOneInput.addEventListener('input', checkForDrawAndTogglePenalties);
        teamTwoInput.addEventListener('input', checkForDrawAndTogglePenalties);

        // Инициализация при зареждане
        checkForDrawAndTogglePenalties();


        if (penaltyCheckbox && penaltyFields) {
            penaltyCheckbox.addEventListener('change', function () {
                if (penaltyCheckbox.checked) {
                    penaltyFields.style.display = 'block';
                } else {
                    penaltyFields.style.display = 'none';
                }
            }); 
        }


    

});
