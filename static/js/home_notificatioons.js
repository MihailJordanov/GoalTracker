document.getElementById("notifications-link").addEventListener("click", function (event) {
    event.preventDefault(); // Спира презареждането
    let container = document.getElementById("notifications-container");

    if (container.style.display === "none") {
        fetch('/get-notifications')
            .then(response => response.json())
            .then(data => {
                let list = document.getElementById("notifications-list");
                list.innerHTML = ""; // Изчиства старите нотификации

                if (data.length === 0) {
                    list.innerHTML = "<li>No notifications</li>";
                } else {
                    data.forEach(notification => {
                        let li = document.createElement("li");
                        li.textContent = notification.title;
                        li.classList.add("notification-item");
                    
                        // Добавяме съответния клас според is_read
                        if (!notification.is_read) {
                            li.classList.add("unread");
                        } else {
                            li.classList.add("read");
                        }
                    
                        li.addEventListener("click", function (event) {
                            event.stopPropagation();
                    
                            // Активиране/деактивиране на детайли
                            let existingDetails = li.querySelector(".notification-details");
                    
                            if (existingDetails) {
                                existingDetails.remove();
                                li.classList.remove("with-details");
                            } else {
                                document.querySelectorAll(".notification-details").forEach(el => el.remove());
                                document.querySelectorAll(".notification-item").forEach(el => el.classList.remove("with-details"));
                    
                                let details = document.createElement("div");
                                details.classList.add("notification-details");
                                details.innerHTML = `
                                    <p><strong>Title:</strong> ${notification.title}</p>
                                    <p><strong>Description:</strong> ${notification.description}</p>
                                `;
                    
                                // Покана
                                if (notification.type == 1) {
                                    let buttonContainer = document.createElement("div");
                                    buttonContainer.classList.add("invite-button-container");
                    
                                    let acceptBtn = document.createElement("button");
                                    acceptBtn.textContent = "Accept";
                                    acceptBtn.classList.add("accept-btn");
                                    acceptBtn.addEventListener("click", () => respondToInvitation(notification.id, true, li));
                    
                                    let denyBtn = document.createElement("button");
                                    denyBtn.textContent = "Deny";
                                    denyBtn.classList.add("deny-btn");
                                    denyBtn.addEventListener("click", () => respondToInvitation(notification.id, false, li));
                    
                                    buttonContainer.appendChild(acceptBtn);
                                    buttonContainer.appendChild(denyBtn);
                                    details.appendChild(buttonContainer);
                                }
                    
                                li.appendChild(details);
                                li.classList.add("with-details");
                    
                                // Маркираме като прочетено
                                if (!notification.is_read) {
                                    li.classList.remove("unread");
                                    li.classList.add("read");
                                    markAsRead(notification.id);
                                }
                            }
                        });
                    
                        list.appendChild(li);
                    });
                    
                }

                container.style.display = "block";
            })
            .catch(error => console.error("Error loading notifications:", error));
    } else {
        container.style.display = "none";
    }
});

// Функция за маркиране като прочетено
function markAsRead(notificationId) {
    fetch(`/mark-notification-read/${notificationId}`, { method: "POST" })
        .catch(error => console.error("Error marking notification as read:", error));
}


function respondToInvitation(notificationId, accept, liElement) {
    console.log("Notification ID:", notificationId); // Проверка на ID-то
    let url = accept ? "/accept-invite" : "/decline-invite";

    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notification_id: notificationId })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Response:", data); // Проверка на отговора от сървъра
        if (data.success) {
            liElement.remove(); // Премахва поканата от списъка
            location.reload(); // Рефрешва страницата след успешното добавяне на играча
        } else {
            alert(data.error || "Something went wrong!");
        }
    })
    .catch(error => console.error("Error handling invitation:", error));
}



// При зареждане на страницата, проверяваме за непрочетени
document.addEventListener("DOMContentLoaded", function () {
    fetch('/get-notifications')
        .then(response => response.json())
        .then(data => {
            let unreadCount = data.filter(n => !n.is_read).length;

            let indicator = document.getElementById("notification-indicator");
            let profileIndicator = document.getElementById("profile-notification-indicator");

            if (indicator) {
                indicator.textContent = unreadCount > 9 ? "!" : unreadCount;
                indicator.style.display = unreadCount > 0 ? "inline-block" : "none";
            }

            if (profileIndicator) {
                profileIndicator.textContent = unreadCount > 9 ? "!" : unreadCount;
                profileIndicator.style.display = unreadCount > 0 ? "inline-block" : "none";
            }
        })
        .catch(error => console.error("Error checking unread notifications:", error));
});


// Закриване на прозореца при клик извън него
document.addEventListener("click", function (event) {
    let container = document.getElementById("notifications-container");
    let notificationsLink = document.getElementById("notifications-link");

    if (container.style.display === "block" &&
        !container.contains(event.target) &&
        !notificationsLink.contains(event.target)) {
        container.style.display = "none";
    }
});

















