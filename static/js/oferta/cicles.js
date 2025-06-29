const CiclesManager = (function () {
    let ciclesSeleccionats = [];
    let totsElsCiclesDisponibles = {};

    function inicialitzarCicles() {
        const select = document.getElementById('select-cicle');
        totsElsCiclesDisponibles = {};

        Array.from(select.children).forEach(node => {
            if (node.tagName === 'OPTGROUP') {
                const familiaNom = node.label;
                totsElsCiclesDisponibles[familiaNom] = totsElsCiclesDisponibles[familiaNom] || [];
                Array.from(node.children).forEach(option => {
                    if (option.value) {
                        totsElsCiclesDisponibles[familiaNom].push({
                            id: option.value,
                            nom: option.dataset.nom,
                            grau: option.dataset.grau,
                            familia: option.dataset.familia
                        });
                    }
                });
            }
        });

        renderitzarCiclesDisponibles();
        renderitzarCiclesSeleccionats();
    }

    function afegirCicle() {
        const select = document.getElementById('select-cicle');
        const selectedOption = select.options[select.selectedIndex];

        if (selectedOption && selectedOption.value) {
            const id = selectedOption.value;
            const nom = selectedOption.dataset.nom;
            const grau = selectedOption.dataset.grau;
            const familia = selectedOption.dataset.familia;

            ciclesSeleccionats.push({ id, nom, grau, familia });

            for (const familiaNom in totsElsCiclesDisponibles) {
                totsElsCiclesDisponibles[familiaNom] = totsElsCiclesDisponibles[familiaNom].filter(c => c.id !== id);
            }

            renderitzarCiclesDisponibles();
            renderitzarCiclesSeleccionats();
        }
    }

    function eliminarCicle(index) {
        const eliminat = ciclesSeleccionats.splice(index, 1)[0];
        const familia = eliminat.familia;
        totsElsCiclesDisponibles[familia] = totsElsCiclesDisponibles[familia] || [];
        totsElsCiclesDisponibles[familia].push(eliminat);
        totsElsCiclesDisponibles[familia].sort((a, b) => a.nom.localeCompare(b.nom));

        renderitzarCiclesDisponibles();
        renderitzarCiclesSeleccionats();
    }

    function renderitzarCiclesDisponibles() {
        const select = document.getElementById('select-cicle');
        select.innerHTML = '<option value="">Selecciona un cicle</option>';
        const families = Object.keys(totsElsCiclesDisponibles).sort();

        families.forEach(familiaNom => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = familiaNom;
            totsElsCiclesDisponibles[familiaNom].forEach(cicle => {
                const option = document.createElement('option');
                option.value = cicle.id;
                option.dataset.nom = cicle.nom;
                option.dataset.grau = cicle.grau;
                option.dataset.familia = cicle.familia;
                option.textContent = `${cicle.nom} (${cicle.grau})`;
                optgroup.appendChild(option);
            });
            select.appendChild(optgroup);
        });
    }

    function renderitzarCiclesSeleccionats() {
        const container = document.getElementById('cicles-container');
        container.innerHTML = '';

        if (ciclesSeleccionats.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-mortarboard" style="font-size: 2rem;"></i>
                    <p class="mt-2 mb-0">No has afegit cap estudi</p>
                    <small>Selecciona els cicles als quals va dirigida l'oferta</small>
                </div>
            `;
            return;
        }

        ciclesSeleccionats.forEach((cicle, index) => {
            const div = document.createElement('div');
            div.className = 'funcio-item p-3 mb-2 rounded d-flex justify-content-between align-items-start';
            div.innerHTML = `
                <div class="flex-grow-1">
                    <strong class="text-primary">${index + 1}.</strong> ${cicle.nom} — <em>${cicle.grau} (${cicle.familia})</em>
                    <input type="hidden" name="cicles" value="${cicle.id}">
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="CiclesManager.eliminarCicle(${index})" title="Eliminar cicle">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            container.appendChild(div);
        });
    }

    return {
        inicialitzarCicles,
        afegirCicle,
        eliminarCicle
    };
})();
