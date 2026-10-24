document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("adminSidebar");
    const menuButton = document.querySelector(".mobile-menu-btn");
    const scrim = document.querySelector(".sidebar-scrim");
    const pages = document.querySelectorAll(".page");
    const menuLinks = document.querySelectorAll(".sidebar .menu a");

    const closeSidebar = () => {
        sidebar?.classList.remove("show");
        scrim?.classList.remove("show");
        document.body.classList.remove("sidebar-open");
        menuButton?.setAttribute("aria-expanded", "false");
        menuButton?.setAttribute("aria-label", "Ouvrir le menu de navigation");
    };

    const showPage = (hash) => {
        const pageId = (hash || "#home").slice(1);
        const target = document.getElementById(pageId);
        if (!target || !target.classList.contains("page")) return;

        pages.forEach((page) => {
            const active = page === target;
            page.classList.toggle("active", active);
            page.setAttribute("aria-hidden", String(!active));
        });

        menuLinks.forEach((link) => {
            const active = link.hash === `#${pageId}`;
            link.classList.toggle("active", active);
            if (active) link.setAttribute("aria-current", "page");
            else link.removeAttribute("aria-current");
        });

        closeSidebar();
    };

    document.addEventListener("click", (event) => {
        const link = event.target.closest('a[href^="#"]');
        if (!link) return;
        const target = document.getElementById(link.hash.slice(1));
        if (!target || !target.classList.contains("page")) return;
        event.preventDefault();
        if (window.location.hash === link.hash) showPage(link.hash);
        else window.location.hash = link.hash;
    });

    window.addEventListener("hashchange", () => showPage(window.location.hash));

    menuButton?.addEventListener("click", () => {
        if (!sidebar) return;
        const isOpen = sidebar.classList.toggle("show");
        scrim?.classList.toggle("show", isOpen);
        document.body.classList.toggle("sidebar-open", isOpen);
        menuButton.setAttribute("aria-expanded", String(isOpen));
        menuButton.setAttribute(
            "aria-label",
            isOpen ? "Fermer le menu de navigation" : "Ouvrir le menu de navigation"
        );
    });
    scrim?.addEventListener("click", closeSidebar);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeSidebar();
    });

    document.querySelectorAll("[data-table-search]").forEach((input) => {
        const table = document.getElementById(input.dataset.tableSearch);
        const body = table?.tBodies[0];
        if (!body) return;

        const noResults = document.createElement("tr");
        noResults.className = "search-empty";
        noResults.hidden = true;
        const message = document.createElement("td");
        message.className = "empty-table";
        message.colSpan = table.tHead?.rows[0]?.cells.length || 1;
        message.textContent = "Aucun résultat ne correspond à votre recherche.";
        noResults.append(message);
        body.append(noResults);

        input.addEventListener("input", () => {
            const query = input.value.trim().toLocaleLowerCase("fr");
            let visibleCount = 0;

            Array.from(body.rows).forEach((row) => {
                if (row === noResults) return;
                const matches = !query || row.textContent.toLocaleLowerCase("fr").includes(query);
                row.hidden = !matches;
                if (matches) visibleCount += 1;
            });
            noResults.hidden = !query || visibleCount > 0;
        });
    });

    const roleSelect = document.getElementById("roleSelect");
    const mairieContainer = document.getElementById("mairieSelectContainer");
    const hopitalContainer = document.getElementById("hopitalSelectContainer");

    const updateRoleFields = () => {
        if (!roleSelect || !mairieContainer || !hopitalContainer) return;
        const role = roleSelect.value;
        mairieContainer.classList.toggle("d-none", role !== "AGENT_MAIRIE");
        hopitalContainer.classList.toggle("d-none", role !== "AGENT_HOPITAL");

        const mairieInput = mairieContainer.querySelector('[name="mairie_id"]');
        const hopitalInput = hopitalContainer.querySelector('[name="hopital_id"]');
        if (mairieInput) mairieInput.required = role === "AGENT_MAIRIE";
        if (hopitalInput) hopitalInput.required = role === "AGENT_HOPITAL";
    };

    roleSelect?.addEventListener("change", updateRoleFields);
    updateRoleFields();
    showPage(window.location.hash);
});
