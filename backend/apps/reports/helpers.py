from rest_framework.exceptions import PermissionDenied

from apps.showrooms.models import Showroom


def resolve_showroom_scope(request):
    """
    Returns the Showroom queryset a user is allowed to report on, and the
    specific showroom_id filter to apply (or None for "all showrooms",
    which is only permitted for Admin).
    """
    user = request.user
    requested_showroom_id = request.query_params.get("showroom")

    if user.role == "admin":
        return Showroom.objects.all(), requested_showroom_id

    # Showroom user: always locked to their own showroom, regardless of
    # what showroom_id was requested in the query string.
    if requested_showroom_id and str(requested_showroom_id) != str(user.showroom_id):
        raise PermissionDenied("You can only access reports for your own showroom.")
    return Showroom.objects.filter(id=user.showroom_id), user.showroom_id
