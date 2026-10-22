/* admin_extras.js — chargé APRÈS admin.js et bootstrap.bundle.min.js
   Aucun code Jinja ici : les données viennent de balises JSON (#graph-data, #flash-data). */
(function () {
    'use strict';

    function normaliser(texte) {
        return (texte || '').toString().toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
    }

    function lireJSON(id, parDefaut) {
        var el = document.getElementById(id);
        if (!el) return parDefaut;
        try { return JSON.parse(el.textContent); } catch (e) { return parDefaut; }
    }

    /* ------------------------------------------------------------------
       1. Filtres de tableaux
          <input data-filter-target="#tableX" data-filter-key="q">          (recherche libre)
          <select data-filter-target="#tableX" data-filter-key="role">      (compare à tr.dataset.role)
          <tr data-role="ADMIN" data-mairie="3"> ...
       ------------------------------------------------------------------ */
    function initFiltres() {
        var groupes = {};
        document.querySelectorAll('[data-filter-target]').forEach(function (controle) {
            var cible = controle.getAttribute('data-filter-target');
            (groupes[cible] = groupes[cible] || []).push(controle);
        });

        Object.keys(groupes).forEach(function (selecteur) {
            var table = document.querySelector(selecteur);
            if (!table) return;

            function appliquer() {
                var visibles = 0;
                table.querySelectorAll('tbody tr').forEach(function (ligne) {
                    var ok = true;
                    groupes[selecteur].forEach(function (controle) {
                        var valeur = normaliser(controle.value);
                        if (!valeur) return;
                        var cle = controle.getAttribute('data-filter-key');
                        if (cle === 'q') {
                            if (normaliser(ligne.textContent).indexOf(valeur) === -1) ok = false;
                        } else if (normaliser(ligne.dataset[cle]) !== valeur) {
                            ok = false;
                        }
                    });
                    ligne.hidden = !ok;
                    if (ok) visibles++;
                });
                var vide = document.querySelector('[data-empty-for="' + selecteur + '"]');
                if (vide) vide.hidden = visibles > 0;
            }

            groupes[selecteur].forEach(function (controle) {
                controle.addEventListener(controle.tagName === 'SELECT' ? 'change' : 'input', appliquer);
            });
        });
    }

    /* ------------------------------------------------------------------
       2. Rôle -> affichage de la mairie / de l'hôpital associé(e)
       ------------------------------------------------------------------ */
    function basculer(boiteMairie, boiteHopital, role) {
        [[boiteMairie, role === 'AGENT_MAIRIE'], [boiteHopital, role === 'AGENT_HOPITAL']].forEach(function (paire) {
            var boite = paire[0], visible = paire[1];
            if (!boite) return;
            boite.classList.toggle('d-none', !visible);
            var select = boite.querySelector('select');
            if (select) {
                select.required = visible;          // obligatoire seulement si visible
                if (!visible) select.value = '';    // évite d'envoyer une association incohérente
            }
        });
    }

    function initRoles() {
        var ajout = document.getElementById('roleSelect');
        if (ajout) {
            var go = function () {
                basculer(document.getElementById('mairieSelectContainer'),
                         document.getElementById('hopitalSelectContainer'), ajout.value);
            };
            ajout.addEventListener('change', go);
            go();
        }
        document.querySelectorAll('.role-select').forEach(function (select) {
            var id = select.getAttribute('data-user');
            select.addEventListener('change', function () {
                basculer(document.getElementById('mairieSelectContainer-' + id),
                         document.getElementById('hopitalSelectContainer-' + id), select.value);
            });
        });
    }

    /* ------------------------------------------------------------------
       3. Confirmation avant action sensible : <form data-confirm="...">
       ------------------------------------------------------------------ */
    function initConfirmations() {
        document.querySelectorAll('form[data-confirm]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                if (!window.confirm(form.getAttribute('data-confirm'))) e.preventDefault();
            });
        });
    }

    /* ------------------------------------------------------------------
       4. Graphiques
       ------------------------------------------------------------------ */
    function initGraphiques() {
        var donnees = lireJSON('graph-data', null);
        var canvases = document.querySelectorAll('canvas[data-chart]');
        if (!donnees || !canvases.length) return;

        if (typeof Chart === 'undefined') {
            canvases.forEach(function (c) {
                var p = document.createElement('p');
                p.className = 'text-muted small mb-0';
                p.textContent = "Graphique indisponible : static/js/chart.min.js est introuvable.";
                c.replaceWith(p);
            });
            return;
        }

        var couleurs = ['rgba(255, 99, 132, 0.75)', 'rgba(54, 162, 235, 0.75)',
                        'rgba(255, 206, 86, 0.75)', 'rgba(75, 192, 192, 0.75)'];

        var actes = document.getElementById('actesChart');
        if (actes) {
            new Chart(actes.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: donnees.actes_months || [],
                    datasets: [{
                        label: 'Actes de naissance',
                        data: donnees.actes_data || [],
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } } }
                }
            });
        }

        [['rolesChart', 'roles_labels', 'roles_data', [couleurs[0], couleurs[1], couleurs[2]]],
         ['statutsChart', 'statuts_labels', 'statuts_data',
          ['rgba(255, 193, 7, 0.8)', 'rgba(25, 135, 84, 0.8)', 'rgba(220, 53, 69, 0.8)', 'rgba(13, 110, 253, 0.8)']]
        ].forEach(function (cfg) {
            var el = document.getElementById(cfg[0]);
            if (!el) return;
            new Chart(el.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: donnees[cfg[1]] || [],
                    datasets: [{ data: donnees[cfg[2]] || [], backgroundColor: cfg[3], borderWidth: 1 }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        });
    }

    /* ------------------------------------------------------------------
       5. Notifications flash (textContent : aucune injection HTML possible)
       ------------------------------------------------------------------ */
    function initNotifications() {
        var messages = lireJSON('flash-data', []);
        var autorises = ['success', 'danger', 'warning', 'info', 'primary', 'secondary'];
        messages.forEach(function (item, index) {
            var categorie = autorises.indexOf(item[0]) !== -1 ? item[0] : 'info';
            var boite = document.createElement('div');
            boite.className = 'alert alert-' + categorie + ' alert-dismissible fade show position-fixed end-0 m-3';
            boite.style.zIndex = '9999';
            boite.style.top = (index * 70) + 'px';
            boite.setAttribute('role', 'alert');

            var texte = document.createElement('span');
            texte.textContent = item[1];

            var fermer = document.createElement('button');
            fermer.type = 'button';
            fermer.className = 'btn-close';
            fermer.setAttribute('data-bs-dismiss', 'alert');
            fermer.setAttribute('aria-label', 'Fermer');

            boite.appendChild(texte);
            boite.appendChild(fermer);
            document.body.appendChild(boite);
            setTimeout(function () { boite.remove(); }, 6000);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initFiltres();
        initRoles();
        initConfirmations();
        initGraphiques();
        initNotifications();
    });
})();