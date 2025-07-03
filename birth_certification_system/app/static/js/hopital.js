document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM entièrement chargé et analysé");

    // Gestion des liens de la sidebar
    const links = document.querySelectorAll(".sidebar .menu li a");

    links.forEach((link) => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const targetId = this.getAttribute("href");
            const targetPage = document.querySelector(targetId);

            if (!targetPage) return;

            // Masquer toutes les pages
            document.querySelectorAll(".page").forEach((page) => {
                page.classList.remove("active");
                page.style.display = "none";
            });

            // Afficher la page cible
            targetPage.classList.add("active");
            targetPage.style.display = "block";

            // Masquer le texte d'accueil s'il existe
            const homeText = document.querySelector(".content p");
            if (homeText) homeText.style.display = "none";
        });
    });

    // Gestion des clics sur les cartes (liens cliquables)
    document.querySelectorAll('.card-link').forEach(card => {
        card.addEventListener('click', function () {
            const target = this.getAttribute('data-target');
            document.querySelectorAll('.page').forEach(page => {
                page.classList.remove('active');
            });
            document.querySelector(target).classList.add('active');
        });
    });

    // 🔍 Filtres et recherche en temps réel
    const inputRecherche = document.getElementById("rechercheDeclaration");
    const selectStatut = document.getElementById("filtreStatut");
    const inputDate = document.getElementById("filtreDate");
    const cartes = document.querySelectorAll(".declaration-card");
    const messageAucun = document.getElementById("messageAucunResultat");

    function filtrerCartes() {
        const recherche = inputRecherche.value.toLowerCase().trim();
        const statut = selectStatut.value;
        const date = inputDate.value;
        let auMoinsUneVisible = false;

        cartes.forEach((carte) => {
            const nom = carte.dataset.nom.toLowerCase();
            const statutCarte = carte.dataset.statut;
            const dateCarte = carte.dataset.date;

            let visible = true;

            if (recherche && !nom.includes(recherche)) {
                visible = false;
            }

            if (statut && statutCarte !== statut) {
                visible = false;
            }


            if (date && dateCarte !== date) {
                visible = false;
            }

            carte.style.display = visible ? "block" : "none";
            if (visible) auMoinsUneVisible = true;
        });

        // Afficher ou masquer le message "aucun résultat"
        messageAucun.style.display = auMoinsUneVisible ? "none" : "block";
    }

    inputRecherche.addEventListener("input", filtrerCartes);
    selectStatut.addEventListener("change", filtrerCartes);
    inputDate.addEventListener("change", filtrerCartes);
});
