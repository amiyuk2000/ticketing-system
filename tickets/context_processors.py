from .permissions import is_manager, role_name


def user_role(request):
    """Make the current user's role available in every template."""
    if not request.user.is_authenticated:
        return {}
    return {
        'user_role': role_name(request.user),
        'user_is_manager': is_manager(request.user),
    }
