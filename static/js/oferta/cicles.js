const CiclesManager = (function () {
    let ciclesSeleccionats = [];
    let totsElsCiclesDisponibles = {};

    function inicialitzarCicles(seleccionats = []) {
        ciclesSeleccionats = Array.isArray(seleccionats) ? seleccionats : [];

        ciclesSeleccionats.forEach(c => c.id = c.id.toString());

        const select = document.getElementById('select-cicle');
        totsElsCiclesDisponibles = {};

        // Carrega tots els cicles disponibles del DOM
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

        // Elimina els seleccionats de les opcions disponibles
        ciclesSeleccionats.forEach(sel => {
            const familia = sel.familia;
            if (totsElsCiclesDisponibles[familia]) {
                totsElsCiclesDisponibles[familia] = totsElsCiclesDisponibles[familia].filter(c => c.id !== sel.id);
            }
        });

        renderitzarCiclesDisponibles();
        renderitzarCiclesSeleccionats();
        select.addEventListener('change', () => {
            CiclesManager.afegirCicle();
            // Reinicia el valor del select per tornar a mostrar el placeholder
            select.value = '';
        });

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

            if (totsElsCiclesDisponibles[familia]) {
                totsElsCiclesDisponibles[familia] = totsElsCiclesDisponibles[familia].filter(c => c.id !== id);
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
        if (!select) return;
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
               
                <button type="button" class="tercer-btn" onclick="CiclesManager.eliminarCicle(${index})" title="Eliminar cicle">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                        <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
                        <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
                   </svg>
                </button>
               
            `;
            container.appendChild(div);
        });
    }

    function getSeleccionats() {
         return [...ciclesSeleccionats];
    }

    return {
        inicialitzarCicles,
        afegirCicle,
        eliminarCicle,
        getSeleccionats
    };
})();
