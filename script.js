
const tabs = document.querySelectorAll(".tab");
const forms = document.querySelectorAll(".login-form");
const message = document.getElementById("message");

tabs.forEach(function(tab) {
    tab.addEventListener("click", function() {
        forms.forEach(function(form) {
            form.classList.add("hidden");
        });

        tabs.forEach(function(item) {
            item.classList.remove("active");
        });

        document.getElementById(tab.dataset.form)
            .classList.remove("hidden");

        tab.classList.add("active");
        message.textContent = "";
    });
});

forms.forEach(function(form) {
    form.addEventListener("submit", function(event) {
        event.preventDefault();

        const fields = form.querySelectorAll("input");

        if (form.id === "admin") {
            const adminUsername = fields[0].value.trim();
            const adminPassword = fields[1].value.trim();
            
            if (adminUsername.toLowerCase() === "sriram" && adminPassword === "333") {
                window.location.href = "http://localhost:5173/admin/login";
            } else {
                message.textContent = "Invalid admin username or password!";
                message.style.color = "red";
            }
            return;
        }

        if (form.id === "register") {
            if (fields[2].value !== fields[3].value) {
                message.textContent = "Passwords do not match.";
                return;
            }

            message.textContent =
                "Registration form validated. Backend needed to save your account.";
            return;
        }

        message.textContent =
            "Form submitted. Connect a backend to verify your login.";
    });
});

