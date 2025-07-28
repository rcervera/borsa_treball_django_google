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
            idiomes.push({ "idioma": nom, "nivell": nivell });
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
            div.className = 'funcio-item p-3 mb-2 rounded d-flex justify-content-between align-items-start';
            div.innerHTML = `
                <div class="flex-grow-1">
                    ${idioma.idioma} — <em>${idioma.nivell}</em>
                    <input type="hidden" name="idiomes_nom" value="${idioma.idioma}">
                    <input type="hidden" name="idiomes_nivell" value="${idioma.nivell}">
                </div>
                <button type="button" class="tercer-btn" onclick="IdiomesManager.eliminarIdioma(${index})" title="Eliminar idioma">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                        <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
                        <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
                   </svg>
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
