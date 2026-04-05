from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"services", views.ServiceViewSet, basename="service")
router.register(r"companies", views.CompanyViewSet, basename="company")
router.register(r"tickets", views.TicketViewSet, basename="ticket")
router.register(r"bots", views.BotConfigViewSet, basename="botconfig")

urlpatterns = [
    # Auth
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/me/", views.me_view, name="me"),

    # Dashboard
    path("dashboard/stats/", views.dashboard_stats, name="dashboard-stats"),

    # Ticket messages
    path("tickets/<uuid:ticket_id>/messages/", views.MessageViewSet.as_view({"get": "list", "post": "create"}), name="ticket-messages"),
    path("tickets/<uuid:ticket_id>/send-media/", views.agent_send_media, name="agent-send-media"),

    # Telegram webhook
    path("webhook/<str:token_hash>/", views.telegram_webhook, name="telegram-webhook"),

    # Internal bot API
    path("internal/create-ticket/", views.bot_create_ticket, name="bot-create-ticket"),
    path("internal/services/", views.bot_get_services, name="bot-get-services"),
    path("internal/user-message/", views.bot_user_message, name="bot-user-message"),
    path("internal/user-media/", views.bot_user_media, name="bot-user-media"),

    # Router
    path("", include(router.urls)),
]
