document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM entièrement chargé et analysé");

    // Gestion des liens de la sidebar
    const links = document.querySelectorAll(".sidebar .menu li a");
    console.log(`Nombre de liens trouvés : ${links.length}`);

    links.forEach((link) => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            console.log(`Lien cliqué : ${this.getAttribute("href")}`);

            const targetId = this.getAttribute("href");
            const targetPage = document.querySelector(targetId);

            if (!targetPage) {
                console.error(`Page cible non trouvée : ${targetId}`);
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
            console.log(`Page affichée : ${targetId}`);

            // Masquer le paragraphe d'accueil s'il existe
            const homeText = document.querySelector(".content p");
            if (homeText) {
                homeText.style.display = "none";
                console.log("Paragraphe d'accueil masqué");
            }
        });
    });
});