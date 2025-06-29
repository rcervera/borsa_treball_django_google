const IdiomesManager = (function () {
    let idiomes = [];

    function getIdiomes() {
         return [...idiomes];
    }

    function inicialitzarIdiomes(dadesInici = []) {
        idiomes = Array.isArray(dadesInici) ? dadesInici : [];
        renderitzarIdiomes();
    }

    function afegirIdioma() {
        const nom = document.getElementById('idioma_nom').value.trim();
        const nivell = document.getElementById('idioma_nivell').value.trim();

        if (nom && nivell) {
            idiomes.push({ nom, nivell });
            document.getElementById('idioma_nom').value = '';
            document.getElementById('idioma_nivell').value = '';
            renderitzarIdiomes();
        }
    }

    function eliminarIdioma(index) {
        idiomes.splice(index, 1);
        renderitzarIdiomes();
    }

    function renderitzarIdiomes() {
        const container = document.getElementById('idiomes-container');
        container.innerHTML = '';

        if (idiomes.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-translate" style="font-size: 2rem;"></i>
                    <p class="mt-2 mb-0">No has afegit cap idioma</p>
                    <small>Pots afegir idiomes i especificar el nivell requerit</small>
                </div>
            `;
            return;
        }

        idiomes.forEach((idioma, index) => {
            const div = document.createElement('div');
            div.className = 'idioma-item p-3 mb-2 rounded d-flex justify-content-between align-items-start';
            div.innerHTML = `
                <div class="flex-grow-1">
                    <strong class="text-primary">${index + 1}.</strong> ${idioma.nom} — <em>${idioma.nivell}</em>
                    <input type="hidden" name="idiomes_nom" value="${idioma.nom}">
                    <input type="hidden" name="idiomes_nivell" value="${idioma.nivell}">
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="IdiomesManager.eliminarIdioma(${index})" title="Eliminar idioma">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            container.appendChild(div);
        });
    }

    return {
        inicialitzarIdiomes,
        afegirIdioma,
        eliminarIdioma,
        getIdiomes
    };
})();
