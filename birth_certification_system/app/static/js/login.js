document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM entièrement chargé");

    // ----- GESTION DE LA NAVIGATION DANS LA SIDEBAR -----
    const links = document.querySelectorAll(".sidebar .menu li a");

    links.forEach((link) => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const targetId = this.getAttribute("href");
            activerPage(targetId);
            mettreLienActif(this);
        });
    });

    // ----- GESTION DU CLIC SUR LES CARTES DU TABLEAU DE BORD -----
    document.querySelectorAll('.card.card-stats').forEach(card => {
        const link = card.querySelector('a[href^="#"]');
        if (link) {
            const targetId = link.getAttribute('href');
            card.setAttribute('data-target', targetId);
            card.classList.add('card-link');

            // clic sur toute la carte
            card.addEventListener('click', function (e) {
                // Ne rien faire si on clique sur le lien directement
                if (e.target.tagName === 'A' || e.target.closest('a')) return;

                activerPage(targetId);
                mettreLienActifSidebar(targetId);
            });

            // clic sur "Voir tous"
            link.addEventListener('click', function (e) {
                e.preventDefault();
                activerPage(targetId);
                mettreLienActifSidebar(targetId);
            });
        }
    });

    // ----- GESTION DE L'AFFICHAGE DYNAMIQUE DES CHAMPS PAR RÔLE -----
    const roleSelect = document.getElementById('roleSelect');
    const mairieContainer = document.getElementById('mairieSelectContainer');
    const hopitalContainer = document.getElementById('hopitalSelectContainer');

    if (roleSelect && mairieContainer && hopitalContainer) {
        roleSelect.addEventListener('change', () => {
            const role = roleSelect.value;
            mairieContainer.classList.toggle('d-none', role !== 'AGENT_MAIRIE');
            hopitalContainer.classList.toggle('d-none', role !== 'AGENT_HOPITAL');

            const mairieInput = mairieContainer.querySelector('[name="mairie_id"]');
            const hopitalInput = hopitalContainer.querySelector('[name="hopital_id"]');

            if (mairieInput && hopitalInput) {
                mairieInput.required = role === 'AGENT_MAIRIE';
                hopitalInput.required = role === 'AGENT_HOPITAL';
            }
        });
    }

    // Optionnel : activer la page courante au chargement si hash dans l'URL
    const initialPage = window.location.hash || "#page1";
    activerPage(initialPage);
    mettreLienActifSidebar(initialPage);
});

/**
 * Affiche la page demandée et masque les autres
 */
function activerPage(idPage) {
    document.querySelectorAll(".page").forEach((page) => {
        page.classList.remove("active");
        page.style.display = "none";
    });

    const targetPage = document.querySelector(idPage);
    if (targetPage) {
        targetPage.style.display = "block";
        setTimeout(() => {
            targetPage.classList.add("active");
        }, 10);
    } else {
        console.error("Page non trouvée : " + idPage);
    }
}

/**
 * Met à jour les liens actifs dans la sidebar
 */
function mettreLienActif(link) {
    document.querySelectorAll(".sidebar .menu li a").forEach((l) => {
        l.classList.remove("active");
        if (l.parentElement) l.parentElement.classList.remove("active");
    });
    link.classList.add("active");
    if (link.parentElement) link.parentElement.classList.add("active");
}

/**
 * Active un lien dans la sidebar à partir d’un ID (utile pour les cartes)
 */
function mettreLienActifSidebar(idPage) {
    const lien = document.querySelector(`.sidebar .menu a[href="${idPage}"]`);
    if (lien) {
        mettreLienActif(lien);
    }
}
