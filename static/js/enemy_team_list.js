document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("toggleFormMode");
    const formManual = document.getElementById("form_manual");
    const formTeamCode = document.getElementById("form_team_code");
    const body = document.body;
    const h1 = document.querySelector("h1");
    const h2 = document.querySelector("h2");
    const toggleLabel = document.querySelector(".toggle-switch label");
    const formSections = document.querySelectorAll(".form-section");
    const teamCodeInput = document.querySelector('input[name="team_code"]');
    const enemyTitle = document.querySelector('.enemy-list-title');


    function applyManualTheme() {
        body.style.background = "linear-gradient(135deg, #001f2f, #003f5f, #005f7f)";
        h1.style.color = "#00eaff";
        h1.style.textShadow = "0 0 10px #00eaff, 0 0 20px #00eaff";
        h2.style.color = "#cccccc";
        toggleLabel.style.borderColor = "#00eaff";
        if (enemyTitle) {
            enemyTitle.style.background = "linear-gradient(90deg, #00eaff 0%, #00ffb7 100%)";
            enemyTitle.style.webkitBackgroundClip = "text";
            enemyTitle.style.webkitTextFillColor = "transparent";
            enemyTitle.style.textShadow = "0 0 8px #00eaff, 0 0 14px #00ffb7";
        }


        formSections.forEach(section => {
            section.style.borderColor = "#00eaff";
            section.style.boxShadow = "0 0 10px rgba(0, 234, 255, 0.3)";
        });
}


    function applyCodeTheme() {
        body.style.background = "linear-gradient(135deg, #2a003f, #3f005f, #5f007f)";
        h1.style.color = "#ff00cc";
        h1.style.textShadow = "0 0 10px #ff00cc, 0 0 20px #ff00cc";
        h2.style.color = "#cccccc";
        toggleLabel.style.borderColor = "#ff00cc";

        if (enemyTitle) {
            enemyTitle.style.background = "linear-gradient(90deg, #ff00cc 0%, #ff8800 100%)";
            enemyTitle.style.webkitBackgroundClip = "text";
            enemyTitle.style.webkitTextFillColor = "transparent";
            enemyTitle.style.textShadow = "0 0 8px #ff00cc, 0 0 14px #ff8800";
        }


        formSections.forEach(section => {
            section.style.borderColor = "#ff00cc";
            section.style.boxShadow = "0 0 10px rgba(255, 0, 204, 0.3)";
        });
    }



    toggle.addEventListener("change", () => {
        if (toggle.checked) {
            formManual.classList.remove("active");
            formTeamCode.classList.add("active");
            applyCodeTheme();
        } else {
            formManual.classList.add("active");
            formTeamCode.classList.remove("active");
            applyManualTheme();
        }
    });

    // Ограничение за team code - точно 6 символа
    if (teamCodeInput) {
        teamCodeInput.addEventListener("input", () => {
            if (teamCodeInput.value.length > 6) {
                teamCodeInput.value = teamCodeInput.value.slice(0, 6);
            }
        });
    }

    // Apply default theme on load
    applyManualTheme();

    // избор на enemy елемент
    const enemyItems = document.querySelectorAll(".enemy-item");
    let selectedItem = null;

    enemyItems.forEach(li => {
        li.addEventListener("click", (e) => {
        // избягай от клик по бутона да не затваря/отваря пак
        if (e.target.closest(".change-logo-form") || e.target.classList.contains("change-logo-btn")) {
            return;
        }

        if (selectedItem && selectedItem !== li) {
            selectedItem.classList.remove("selected");
            const prevActions = selectedItem.querySelector(".enemy-actions");
            if (prevActions) prevActions.style.display = "none";
        }

        if (li.classList.contains("selected")) {
            li.classList.remove("selected");
            const actions = li.querySelector(".enemy-actions");
            if (actions) actions.style.display = "none";
            selectedItem = null;
        } else {
            li.classList.add("selected");
            const actions = li.querySelector(".enemy-actions");
            if (actions) actions.style.display = "block";
            selectedItem = li;
        }
        });

        // бутон Change logo -> отваря file input
        const btn = li.querySelector(".change-logo-btn");
        if (btn) {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const fileInput = li.querySelector('.change-logo-form input[type="file"]');
            if (fileInput) fileInput.click();
            });
        }
    });
});


function previewImage(event) {
    const input = event.target;
    const file = input.files[0];
    const button = document.querySelector('.custom-file-upload');
    const maxSize = 8 * 1024 * 1024; // 8MB

    if (!file) {
        // Ако потребителят не е избрал нов файл – не прави нищо
        return;
    }

    if (!file.type.startsWith("image/")) {
        alert("Please select a valid image file.");
        input.value = "";
        return;
    }

    if (file.size > maxSize) {
        alert("File size must be less than 8MB.");
        input.value = "";
        return;
    }

    const imageUrl = URL.createObjectURL(file);
    button.style.backgroundImage = 'url(' + imageUrl + ')';
    button.style.backgroundSize = 'cover';
    button.style.backgroundPosition = 'center';
    button.classList.add('selected');
}
