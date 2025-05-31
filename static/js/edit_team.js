function previewImage(event) {
    const input = event.target;
    const file = input.files[0];
    const maxSize = 8 * 1024 * 1024; // 8MB

    if (!file) return;

    // Проверка дали е изображение
    if (!file.type.startsWith("image/")) {
        alert("Please select a valid image file.");
        input.value = "";
        return;
    }

    // Проверка за размер
    if (file.size > maxSize) {
        alert(`The selected image is too large (${(file.size / (1024 * 1024)).toFixed(2)} MB). Please choose an image under 8MB.`);
        input.value = "";
        return;
    }

    // Преглед в <img id="preview">
    let preview = document.getElementById('preview');
    if (!preview) {
        preview = document.createElement("img");
        preview.id = "preview";
        preview.style.width = "150px";
        preview.style.height = "150px";
        preview.style.objectFit = "contain";
        preview.style.borderRadius = "10px";
        preview.style.border = "3px solid #FFD700";
        preview.style.boxShadow = "0 4px 10px rgba(0, 0, 0, 0.1)";
        preview.style.marginTop = "10px";

        const container = document.getElementById("current-logo");
        container.innerHTML = "";
        container.appendChild(preview);
    }

    preview.src = URL.createObjectURL(file);
}

function updateTeamTextColor(color) {
    const teamName = document.getElementById('team-name-preview');
    if (teamName) {
        teamName.style.color = color; // ✅ променя цвета на текста, не на фона
    }
}

function updateTeamNameBgColor(color) {
    const teamName = document.getElementById('team-name-preview');
    if (teamName) {
        teamName.style.backgroundColor = color;
    }
}


function previewBgImage(event) {
    const input = event.target;
    const file = input.files[0];

    if (!file || !file.type.startsWith("image/")) {
        alert("Please select a valid image file.");
        input.value = "";
        return;
    }

    const imageUrl = URL.createObjectURL(file);

    // Преглед в миниатюра, но НЕ променяме preview стила
    const bgPreview = document.getElementById("bg-preview");
    if (bgPreview) {
        bgPreview.src = imageUrl;
    }
}


function toggleBgImageUpload(checked) {
    const section = document.getElementById("bg-image-section");
    if (section) {
        section.style.display = checked ? "block" : "none";
    }
}


document.addEventListener("DOMContentLoaded", function () {
    const bgCheckbox = document.getElementById("enable_bg_image");
    if (bgCheckbox) {
        toggleBgImageUpload(bgCheckbox.checked);
    }

    // Промяна на името в preview
    const nameInput = document.getElementById("team_name_input");
    const namePreview = document.getElementById("team-name-preview");
    if (nameInput && namePreview) {
        nameInput.addEventListener("input", function () {
            namePreview.textContent = nameInput.value.substring(0, 12);
        });
    }
});


function copyTeamCode() {
    const codeEl = document.getElementById("team-code");
    const msgEl = document.getElementById("copied-msg");

    const code = codeEl.innerText;
    navigator.clipboard.writeText(code).then(() => {
        msgEl.style.opacity = 1;

        setTimeout(() => {
            msgEl.style.opacity = 0;
        }, 1000);
    });
}

