const CapacitatsManager = (function () {
    let capacitatsLliures = [];

    function getCapacitats() {
         return [...capacitatsLliures];
    }


    function inicialitzarCapacitats(dadesInici = []) {
        capacitatsLliures = Array.isArray(dadesInici) ? dadesInici : [];
        renderitzarCapacitats();
    }

    function afegirCapacitatLliure() {
        const input = document.getElementById('nova-capacitat-lliure');
        const capacitat = input.value.trim();
       
        if (capacitat && !capacitatsLliures.includes(capacitat)) {
            capacitatsLliures.push(capacitat);
            input.value = '';
            renderitzarCapacitats();
        }
    }

    function eliminarCapacitat(index) {
        capacitatsLliures.splice(index, 1);
        renderitzarCapacitats();
    }

    function renderitzarCapacitats() {
        const container = document.getElementById('capacitatsLliures-container');
        container.innerHTML = '';

        if (capacitatsLliures.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-stars" style="font-size: 2rem;"></i>
                    <p class="mt-2 mb-0">No has afegit cap capacitat</p>
                    <small>Pots afegir competències personals, socials o transversals</small>
                </div>
            `;
            return;
        }

        capacitatsLliures.forEach((cap, index) => {
            const div = document.createElement('div');
            div.className = 'funcio-item p-3 mb-2 rounded d-flex justify-content-between align-items-start';
            div.innerHTML = `
                <div class="flex-grow-1">
                    ${cap}
                    <input type="hidden" name="capacitats" value="${cap}">
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="CapacitatsManager.eliminarCapacitat(${index})" title="Eliminar capacitat">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            container.appendChild(div);
        });
    }

    return {
        inicialitzarCapacitats,
        afegirCapacitatLliure,
        eliminarCapacitat,
        getCapacitats
    };
})();
