from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Only super admins can access."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsAgentOrSuperAdmin(BasePermission):
    """Agents and super admins can access."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ("super_admin", "agent")


class CanAccessTicket(BasePermission):
    """
    Agents can only access tickets for their allowed services.
    Super admins can access everything.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin:
            return True
        # Agent can only see tickets for services they're assigned to
        return obj.service in request.user.allowed_services.all()


class IsTicketOwnerOrSuperAdmin(BasePermission):
    """
    Only the assigned agent or super admin can modify a ticket.
    Used for transfer, status changes, etc.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin:
            return True
        return obj.assigned_agent == request.user
