function previewImage(event) {
    let input = event.target;
    let file = input.files[0];
    let preview = document.getElementById("preview");
    let imagePreview = document.getElementById("imagePreview");
    let fileNameDisplay = document.getElementById("file-name");
    let maxSize = 8 * 1024 * 1024; // 8MB
    let button = document.querySelector('.custom-file-upload');

    if (file) {
        // Проверка дали е изображение
        if (!file.type.startsWith("image/")) {
            alert("Please select a valid image file.");
            input.value = "";
            return;
        }

        // Проверка за размер
        if (file.size > maxSize) {
            alert("File size must be less than 8MB.");
            input.value = "";
            return;
        }

        // Покажи изображението като фон на бутона
        let imageUrl = URL.createObjectURL(file);
        button.style.backgroundImage = 'url(' + imageUrl + ')';
        button.classList.add('selected');
        imagePreview.style.display = "none";

        // По желание: покажи името на файла
        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
        }

    } else {
        // Ако потребителят премахне избора
        button.style.backgroundImage = '';
        button.classList.remove('selected');
        if (fileNameDisplay) {
            fileNameDisplay.textContent = "Choose a file";
        }
    }
}
