document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM entièrement chargé");

    const links = document.querySelectorAll(".sidebar .menu li a");

    links.forEach((link) => {
        link.addEventListener("click", function (e) {
            e.preventDefault();

            const targetId = this.getAttribute("href");
            const targetPage = document.querySelector(targetId);

            if (!targetPage) {
                console.error("Page non trouvée : " + targetId);
                return;
            }

            // Masquer toutes les pages
            document.querySelectorAll(".page").forEach((page) => {
                page.classList.remove("active");
                page.style.display = "none";
            });

            // Afficher la page cible
            targetPage.classList.add("active");
            targetPage.style.display = "block";

            // Mise à jour des liens actifs
            links.forEach((l) => l.classList.remove("active"));
            this.classList.add("active");
        });
    });

    const roleSelect = document.getElementById('roleSelect');
    const mairieContainer = document.getElementById('mairieSelectContainer');
    const hopitalContainer = document.getElementById('hopitalSelectContainer');

    if (roleSelect && mairieContainer && hopitalContainer) {
        roleSelect.addEventListener('change', () => {
            const role = roleSelect.value;
            mairieContainer.classList.toggle('d-none', role !== 'AGENT_MAIRIE');
            hopitalContainer.classList.toggle('d-none', role !== 'AGENT_HOPITAL');
        });
    }
});

// Gestion du clic sur les cartes
document.querySelectorAll('.card-link').forEach(card => {
    card.addEventListener('click', function () {
        const target = this.getAttribute('data-target');
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        document.querySelector(target).classList.add('active');
    });
});