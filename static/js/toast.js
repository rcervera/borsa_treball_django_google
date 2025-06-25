/**
 * Sistema de notificacions Toast per Django
 * Utilitza Bootstrap 5 per mostrar notificacions elegants
 */

// Import Bootstrap
const bootstrap = window.bootstrap;

/**
 * Mostra un toast amb el missatge i tipus especificat
 * @param {string} message - El missatge a mostrar
 * @param {string} type - El tipus de toast ('success', 'error', 'warning', 'info')
 */
function showToast(message, type = 'info') {
    // Crear toast notification
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const bgClass = getToastBgClass(type);
    const iconClass = getToastIcon(type);
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${iconClass} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Tancar"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { 
        delay: 4000,
        autohide: true 
    });
    
    toast.show();
    
    // Eliminar el toast del DOM després que es tanqui
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * Crea el contenidor de toasts si no existeix
 * @returns {HTMLElement} El contenidor de toasts
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

/**
 * Retorna la classe CSS per al fons del toast segons el tipus
 * @param {string} type - El tipus de toast
 * @returns {string} La classe CSS
 */
function getToastBgClass(type) {
    const classes = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    };
    return classes[type] || 'bg-info';
}

/**
 * Retorna la classe d'icona Bootstrap per al toast segons el tipus
 * @param {string} type - El tipus de toast
 * @returns {string} La classe d'icona
 */
function getToastIcon(type) {
    const icons = {
        'success': 'check-circle-fill',
        'error': 'exclamation-triangle-fill',
        'warning': 'exclamation-triangle-fill',
        'info': 'info-circle-fill'
    };
    return icons[type] || 'info-circle-fill';
}

/**
 * Funcions d'accés ràpid per diferents tipus de toasts
 */
function showSuccessToast(message) {
    showToast(message, 'success');
}

function showErrorToast(message) {
    showToast(message, 'error');
}

function showWarningToast(message) {
    showToast(message, 'warning');
}

function showInfoToast(message) {
    showToast(message, 'info');
}

// Fer les funcions globals disponibles
window.showToast = showToast;
window.showSuccessToast = showSuccessToast;
window.showErrorToast = showErrorToast;
window.showWarningToast = showWarningToast;
window.showInfoToast = showInfoToast;