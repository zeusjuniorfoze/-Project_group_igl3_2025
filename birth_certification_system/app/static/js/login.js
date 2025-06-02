const home = document.querySelector(".home"),
    formContainer = document.querySelector(".form_container"),
    formCloseBtn = document.querySelector(".form_close"),
    signupBtn = document.querySelector("#signup"),
    loginBtn = document.querySelector("#login"),
    pwShowHide = document.querySelectorAll(".pw_hide");

// Fermer le formulaire
if (formCloseBtn) {
    formCloseBtn.addEventListener("click", () => home.classList.remove("show"));
}

// Afficher / masquer mot de passe
pwShowHide.forEach((icon) => {
    icon.addEventListener("click", () => {
        let getPwInput = icon.parentElement.querySelector("input");
        if (getPwInput.type === "password") {
            getPwInput.type = "text";
            icon.classList.replace("bx-low-vision", "bx-show");
        } else {
            getPwInput.type = "password";
            icon.classList.replace("bx-show", "bx-low-vision");
        }
    });
});

// Changer entre login et signup
signupBtn.addEventListener("click", (e) => {
    e.preventDefault();
    formContainer.classList.add("active");
});
loginBtn.addEventListener("click", (e) => {
    e.preventDefault();
    formContainer.classList.remove("active");
});

// Validation JS
document.addEventListener('DOMContentLoaded', () => {
    const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    const evaluatePassword = (password) => {
        const length = password.length >= 8;
        const special = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        const number = /[0-9]/.test(password);
        if (length && special && number) return 'green';
        if (length) return 'orange';
        return 'red';
    };
    const showValidationMessage = (element, message, className) => {
        const el = document.getElementById(element);
        el.textContent = message;
        el.className = `validity-message ${className}`;
    };

    // Login form
    const loginEmail = document.getElementById('login-email');
    const loginPassword = document.getElementById('login-password');
    const loginForm = document.querySelector('.login_form form');

    loginEmail.addEventListener('input', () => {
        showValidationMessage('email-message',
            validateEmail(loginEmail.value) ? 'Email valide.' : 'Email invalide.',
            validateEmail(loginEmail.value) ? 'green' : 'red'
        );
    });

    loginPassword.addEventListener('input', () => {
        const strength = evaluatePassword(loginPassword.value);
        let msg = '';
        if (strength === 'green') msg = 'Mot de passe fort.';
        else if (strength === 'orange') msg = 'Mot de passe moyen.';
        else msg = 'Mot de passe trop court.';
        showValidationMessage('password-message', msg, strength);
    });

    loginForm.addEventListener('submit', (e) => {
        if (!validateEmail(loginEmail.value) || evaluatePassword(loginPassword.value) === 'red') {
            e.preventDefault();
            alert('Email invalide ou mot de passe trop faible.');
        }
    });

    // Signup form
    const signupForm = document.querySelector('.signup_form form');
    const signupEmail = document.getElementById('signup-email');
    const signupPassword = document.getElementById('signup-password');
    const confirmPassword = document.getElementById('confirm-password');

    signupEmail.addEventListener('input', () => {
        showValidationMessage('signup-email-message',
            validateEmail(signupEmail.value) ? 'Email valide.' : 'Email invalide.',
            validateEmail(signupEmail.value) ? 'green' : 'red'
        );
    });

    signupPassword.addEventListener('input', () => {
        const strength = evaluatePassword(signupPassword.value);
        let msg = '';
        if (strength === 'green') msg = 'Mot de passe fort.';
        else if (strength === 'orange') msg = 'Mot de passe moyen.';
        else msg = 'Mot de passe trop court.';
        showValidationMessage('signup-password-message', msg, strength);
    });

    confirmPassword.addEventListener('input', () => {
        showValidationMessage('confirm-password-message',
            confirmPassword.value === signupPassword.value ? 'Les mots de passe correspondent.' : 'Les mots de passe ne correspondent pas.',
            confirmPassword.value === signupPassword.value ? 'green' : 'red'
        );
    });

    signupForm.addEventListener('submit', (e) => {
        const emailValid = validateEmail(signupEmail.value);
        const strength = evaluatePassword(signupPassword.value);
        const match = confirmPassword.value === signupPassword.value;
        if (!emailValid || strength === 'red' || !match) {
            e.preventDefault();
            alert('Veuillez corriger les erreurs avant de valider.');
        }
    });
});
