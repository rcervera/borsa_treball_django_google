const FuncionsManager = (function () {
    let funcions = [];

    function inicialitzarFuncions(dadesInici = []) {
        funcions = Array.isArray(dadesInici) ? dadesInici : [];
        renderitzarFuncions();
    }

    function afegirFuncio() {
        const input = document.getElementById('nova-funcio');
        const descripcio = input.value.trim();
        if (descripcio) {
            funcions.push(descripcio);
            input.value = '';
            input.focus();
            renderitzarFuncions();
        }
    }

    function eliminarFuncio(index) {
        funcions.splice(index, 1);
        renderitzarFuncions();
    }

    function renderitzarFuncions() {
        const container = document.getElementById('funcions-container');
        container.innerHTML = '';

        if (funcions.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-list-task" style="font-size: 2rem;"></i>
                    <p class="mt-2 mb-0">Encara no has afegit cap funció</p>
                    <small>Afegeix les funcions principals del càrrec</small>
                </div>
            `;
            return;
        }

        funcions.forEach((funcio, index) => {
            const div = document.createElement('div');
            div.className = 'funcio-item p-3 mb-2 rounded d-flex justify-content-between align-items-start';
            div.innerHTML = `
                <div class="flex-grow-1">
                    <strong class="text-primary">${index + 1}.</strong> ${funcio}
                    <input type="hidden" name="funcions" value="${funcio}">
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="FuncionsManager.eliminarFuncio(${index})" title="Eliminar funció">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            container.appendChild(div);
        });
    }

    return {
        inicialitzarFuncions,
        afegirFuncio,
        eliminarFuncio
    };
})();
