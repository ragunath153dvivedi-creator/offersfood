from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Service, Company, Ticket, Message, BotConfig, TicketTransferLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "is_online", "is_active"]
    list_filter = ["role", "is_online", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Agent Settings", {"fields": ("role", "allowed_services", "is_online", "max_concurrent_tickets")}),
    )
    filter_horizontal = ["allowed_companies"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "display_order", "is_active"]
    list_editable = ["display_order", "is_active"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "service", "display_order", "is_active"]
    list_filter = ["service"]
    list_editable = ["display_order", "is_active"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["ticket_number", "service", "company", "status", "assigned_agent", "created_at"]
    list_filter = ["status", "service", "priority"]
    search_fields = ["ticket_number"]
    readonly_fields = ["ticket_number", "created_at", "updated_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["ticket", "sender_type", "content_preview", "created_at"]
    list_filter = ["sender_type"]

    def content_preview(self, obj):
        return obj.content[:80]


@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "bot_username", "status", "priority", "last_health_check"]
    list_editable = ["priority", "status"]


@admin.register(TicketTransferLog)
class TicketTransferLogAdmin(admin.ModelAdmin):
    list_display = ["ticket", "from_agent", "to_agent", "created_at"]
