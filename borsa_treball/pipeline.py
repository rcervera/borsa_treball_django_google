from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib import messages

def skip_if_user_not_registered(strategy, details, user=None, *args, **kwargs):
    User = get_user_model()
    email = details.get('email')

    if user:   # Si ja està autenticat, no cal fer res
        return

    if not email:  # Si no hi ha email, denegem
        messages.error(strategy.request, "No s'ha proporcionat cap adreça d'email.")
        raise PermissionDenied("No s'ha proporcionat cap adreça d'email.")
    
    try:
        user = User.objects.get(email=email)
        if not user.is_active:  # Comprovem si l'usuari està actiu
            messages.error(strategy.request, "El teu compte està desactivat. Contacta amb l'administrador.")
            raise PermissionDenied("El teu compte està desactivat. Contacta amb l'administrador.")
        return {'user': user}
    except User.DoesNotExist:
        messages.error(strategy.request, "Aquest correu no està registrat.")
        raise PermissionDenied("Aquest compte no està registrat.")
    

