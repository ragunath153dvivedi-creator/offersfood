import os
import hashlib
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count
from django.core.files.base import ContentFile
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import User, Service, Company, Ticket, Message, BotConfig, TicketTransferLog
from .serializers import (
    LoginSerializer, UserSerializer, UserCreateSerializer,
    ServiceSerializer, ServiceListSerializer, CompanySerializer,
    TicketSerializer, TicketSuperAdminSerializer, TicketListSerializer,
    MessageSerializer, TicketTransferSerializer, TransferLogSerializer,
    BotConfigSerializer,
)
from .permissions import IsSuperAdmin, IsAgentOrSuperAdmin, CanAccessTicket, IsTicketOwnerOrSuperAdmin

BOT_INTERNAL_KEY = os.getenv("BOT_INTERNAL_KEY", "bot-internal-secret")


def _check_internal_key(request):
    return request.headers.get("X-Internal-Key") == BOT_INTERNAL_KEY


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    user.is_online = True
    user.save(update_fields=["is_online"])
    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    request.user.is_online = False
    request.user.save(update_fields=["is_online"])
    return Response({"detail": "Logged out"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


# ── Users (Super Admin) ──────────────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsSuperAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        qs = User.objects.all().order_by("-created_at")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response(UserSerializer(user).data)


# ── Services & Companies ──────────────────────────────────────────────────────

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    permission_classes = [IsAgentOrSuperAdmin]

    def get_serializer_class(self):
        return ServiceSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSuperAdmin()]
        return super().get_permissions()


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSuperAdmin()]
        return [IsAgentOrSuperAdmin()]

    def get_queryset(self):
        qs = Company.objects.select_related("service").all()
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs


# ── Tickets ───────────────────────────────────────────────────────────────────

class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAgentOrSuperAdmin]
    http_method_names = ["get", "post", "patch", "head"]

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        if self.request.user.is_super_admin:
            return TicketSuperAdminSerializer
        return TicketSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related("service", "company", "assigned_agent")

        if not user.is_super_admin:
            qs = qs.filter(company__in=user.allowed_companies.all())
            
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        service_filter = self.request.query_params.get("service")
        if service_filter:
            qs = qs.filter(service_id=service_filter)

        assigned = self.request.query_params.get("assigned_to")
        if assigned == "me":
            qs = qs.filter(assigned_agent=user)
        elif assigned == "unassigned":
            qs = qs.filter(assigned_agent__isnull=True, status="open")
        elif assigned:
            qs = qs.filter(assigned_agent_id=assigned)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(ticket_number__icontains=search) | Q(company__name__icontains=search))

        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def pick(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status != Ticket.Status.OPEN:
            return Response({"error": "Ticket is not open for pickup"}, status=status.HTTP_400_BAD_REQUEST)

        active_count = request.user.assigned_tickets.filter(status__in=["assigned", "in_progress"]).count()
        if active_count >= request.user.max_concurrent_tickets:
            return Response({"error": f"Limit of {request.user.max_concurrent_tickets} concurrent tickets reached"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            ticket = Ticket.objects.select_for_update().get(pk=pk)
            if ticket.assigned_agent is not None:
                return Response({"error": "Ticket already picked"}, status=status.HTTP_409_CONFLICT)
            ticket.assigned_agent = request.user
            ticket.status = Ticket.Status.ASSIGNED
            ticket.assigned_at = timezone.now()
            ticket.save(update_fields=["assigned_agent", "status", "assigned_at", "updated_at"])

        Message.objects.create(ticket=ticket, sender_type=Message.SenderType.SYSTEM, content="Ticket picked up by an agent.")
        _notify_user_via_telegram(ticket.telegram_chat_id, f"✅ Your ticket {ticket.ticket_number} has been picked up! An agent will assist you shortly.")
        _broadcast_ticket_update(ticket)
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        ticket = self.get_object()
        if not request.user.is_super_admin and ticket.assigned_agent != request.user:
            return Response({"error": "Only the assigned agent can transfer"}, status=status.HTTP_403_FORBIDDEN)

        serializer = TicketTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            to_agent = User.objects.get(id=serializer.validated_data["to_agent_id"], role__in=["agent", "super_admin"], is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        if not to_agent.is_super_admin:
            if not to_agent.allowed_companies.filter(id=ticket.company_id).exists():
                return Response({"error": "Agent doesn't have access to this company"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            TicketTransferLog.objects.create(ticket=ticket, from_agent=ticket.assigned_agent, to_agent=to_agent, reason=serializer.validated_data.get("reason", ""))
            ticket.assigned_agent = to_agent
            ticket.save(update_fields=["assigned_agent", "updated_at"])

        Message.objects.create(ticket=ticket, sender_type=Message.SenderType.SYSTEM, content="Ticket transferred to another agent.")
        _broadcast_ticket_update(ticket)
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(Ticket.Status.choices):
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_super_admin and ticket.assigned_agent != request.user:
            return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        ticket.status = new_status
        update_fields = ["status", "updated_at"]
        if new_status in ("resolved", "closed"):
            ticket.resolved_at = timezone.now()
            update_fields.append("resolved_at")
            _notify_user_via_telegram(ticket.telegram_chat_id, f"🎉 Your ticket {ticket.ticket_number} has been resolved. Thank you!")

        ticket.save(update_fields=update_fields)
        Message.objects.create(ticket=ticket, sender_type=Message.SenderType.SYSTEM, content=f"Status changed to {ticket.get_status_display()}.")
        _broadcast_ticket_update(ticket)
        return Response(TicketSerializer(ticket).data)


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAgentOrSuperAdmin]
    http_method_names = ["get", "post", "head"]

    def get_queryset(self):
        ticket_id = self.kwargs.get("ticket_id")
        qs = Message.objects.filter(ticket_id=ticket_id).select_related("sender_agent")
        if not self.request.user.is_super_admin:
            qs = qs.filter(Q(is_internal_note=False) | Q(is_internal_note=True, sender_agent=self.request.user))
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        ticket_id = self.kwargs["ticket_id"]
        ticket = Ticket.objects.get(pk=ticket_id)
        msg = serializer.save(ticket=ticket, sender_type=Message.SenderType.AGENT, sender_agent=self.request.user)
        if not msg.is_internal_note and msg.content:
            _notify_user_via_telegram(ticket.telegram_chat_id, msg.content)
        _broadcast_message(ticket, msg)


@api_view(["POST"])
@permission_classes([IsAgentOrSuperAdmin])
def agent_send_media(request, ticket_id):
    """Agent uploads a media file to send to the customer."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    caption = request.data.get("caption", "")
    is_internal = request.data.get("is_internal_note", "false").lower() == "true"

    ct = uploaded_file.content_type or ""
    if ct.startswith("image/"):
        media_type = "image"
    elif ct.startswith("video/"):
        media_type = "video"
    elif ct.startswith("audio/"):
        media_type = "audio"
    else:
        media_type = "document"

    msg = Message.objects.create(
        ticket=ticket, sender_type=Message.SenderType.AGENT, sender_agent=request.user,
        content=caption, is_internal_note=is_internal,
        media_type=media_type, media_file=uploaded_file,
        media_filename=uploaded_file.name, media_size=uploaded_file.size,
    )

    if not is_internal:
        _send_media_to_telegram(ticket.telegram_chat_id, msg)

    _broadcast_message(ticket, msg)
    return Response(MessageSerializer(msg, context={"request": request}).data, status=status.HTTP_201_CREATED)


# ── Bot Webhook ───────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request, token_hash):
    data = request.data
    bot = None
    for bc in BotConfig.objects.filter(status__in=["active", "standby"]):
        if hashlib.sha256(bc.token.encode()).hexdigest()[:16] == token_hash:
            bot = bc
            break
    if not bot:
        return Response(status=status.HTTP_404_NOT_FOUND)

    message = data.get("message") or data.get("callback_query", {}).get("message")
    if message and message.get("text"):
        chat_id = message["chat"]["id"]
        text = message["text"]
        active_ticket = Ticket.objects.filter(telegram_chat_id=chat_id, status__in=["assigned", "in_progress"], assigned_agent__isnull=False).first()
        if active_ticket and not text.startswith("/"):
            msg = Message.objects.create(ticket=active_ticket, sender_type=Message.SenderType.USER, content=text)
            _broadcast_message(active_ticket, msg)

    return Response({"ok": True})


# ── Bot Config ────────────────────────────────────────────────────────────────

class BotConfigViewSet(viewsets.ModelViewSet):
    queryset = BotConfig.objects.all()
    serializer_class = BotConfigSerializer
    permission_classes = [IsSuperAdmin]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        bot = self.get_object()
        BotConfig.objects.filter(status="active").update(status="standby")
        bot.status = "active"
        bot.save(update_fields=["status"])
        return Response(BotConfigSerializer(bot).data)

    @action(detail=True, methods=["post"])
    def health_check(self, request, pk=None):
        bot = self.get_object()
        import requests as req
        try:
            resp = req.get(f"https://api.telegram.org/bot{bot.token}/getMe", timeout=10)
            if resp.status_code == 200:
                bot.bot_username = resp.json().get("result", {}).get("username", "")
                bot.status = "active" if bot.status == "active" else "standby"
                bot.last_error = ""
            else:
                bot.status = "banned" if resp.status_code == 401 else "error"
                bot.last_error = f"HTTP {resp.status_code}"
        except Exception as e:
            bot.status = "error"
            bot.last_error = str(e)[:200]
        bot.last_health_check = timezone.now()
        bot.save()
        return Response(BotConfigSerializer(bot).data)


# ── Dashboard Stats ───────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAgentOrSuperAdmin])
def dashboard_stats(request):
    user = request.user
    base_qs = Ticket.objects.all()
    if not user.is_super_admin:
        base_qs = base_qs.filter(company__in=user.allowed_companies.all())
    stats = {
        "total_tickets": base_qs.count(),
        "open_tickets": base_qs.filter(status="open").count(),
        "assigned_tickets": base_qs.filter(status__in=["assigned", "in_progress"]).count(),
        "resolved_tickets": base_qs.filter(status__in=["resolved", "closed"]).count(),
        "my_tickets": base_qs.filter(assigned_agent=user, status__in=["assigned", "in_progress"]).count(),
    }
    if user.is_super_admin:
        stats["online_agents"] = User.objects.filter(role="agent", is_online=True).count()
        stats["total_agents"] = User.objects.filter(role="agent").count()
        stats["by_service"] = list(base_qs.values("service__name").annotate(count=Count("id")).order_by("-count"))
    return Response(stats)


# ── Internal Bot API ──────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def bot_create_ticket(request):
    if not _check_internal_key(request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    data = request.data
    try:
        service = Service.objects.get(id=data["service_id"])
        company = Company.objects.get(id=data["company_id"])
    except (Service.DoesNotExist, Company.DoesNotExist):
        return Response({"error": "Invalid service or company"}, status=status.HTTP_400_BAD_REQUEST)

    ticket = Ticket.objects.create(
        telegram_user_id=data["telegram_user_id"], telegram_chat_id=data["telegram_chat_id"],
        telegram_username=data.get("telegram_username", ""), telegram_first_name=data.get("telegram_first_name", ""),
        service=service, company=company, form_data=data.get("form_data", {}), bot_token_hash=data.get("bot_token_hash", ""),
    )
    _broadcast_ticket_update(ticket)
    return Response({"ticket_id": str(ticket.id), "ticket_number": ticket.ticket_number}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def bot_get_services(request):
    if not _check_internal_key(request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    services = Service.objects.filter(is_active=True).prefetch_related("companies")
    data = []
    for svc in services:
        data.append({
            "id": str(svc.id), "name": svc.name, "icon": svc.icon,
            "companies": [
                {"id": str(c.id), "name": c.name, "icon": c.icon, "form_schema": c.form_schema, "welcome_message": c.welcome_message, "ticket_created_message": c.ticket_created_message}
                for c in svc.companies.filter(is_active=True).order_by("display_order")
            ],
        })
    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
def bot_user_message(request):
    """Text message from Telegram user."""
    if not _check_internal_key(request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    ticket_id = request.data.get("ticket_id")
    content = request.data.get("content", "").strip()
    if not ticket_id or not content:
        return Response({"error": "Missing data"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
    msg = Message.objects.create(ticket=ticket, sender_type=Message.SenderType.USER, content=content)
    _broadcast_message(ticket, msg)
    return Response({"ok": True}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def bot_user_media(request):
    """Media message from Telegram user (bot uploads the file)."""
    if not _check_internal_key(request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    ticket_id = request.data.get("ticket_id")
    uploaded_file = request.FILES.get("file")
    if not ticket_id or not uploaded_file:
        return Response({"error": "Missing data"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

    msg = Message.objects.create(
        ticket=ticket, sender_type=Message.SenderType.USER,
        content=request.data.get("caption", ""),
        media_type=request.data.get("media_type", "document"),
        media_file=uploaded_file,
        media_filename=request.data.get("media_filename", uploaded_file.name),
        media_size=uploaded_file.size,
    )
    _broadcast_message(ticket, msg)
    return Response({"ok": True}, status=status.HTTP_201_CREATED)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_bot_token():
    from django.conf import settings
    bot = BotConfig.get_active_bot()
    if bot:
        return bot.token
    if settings.TELEGRAM_BOT_TOKENS:
        return settings.TELEGRAM_BOT_TOKENS[0]
    return None


def _notify_user_via_telegram(chat_id, text):
    import requests as req
    token = _get_bot_token()
    if not token:
        return
    try:
        req.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception:
        pass


def _send_media_to_telegram(chat_id, msg):
    """Send a media file to Telegram user."""
    import requests as req
    token = _get_bot_token()
    if not token or not msg.media_file:
        return

    try:
        method_map = {"image": ("sendPhoto", "photo"), "video": ("sendVideo", "video"), "audio": ("sendAudio", "audio"), "document": ("sendDocument", "document")}
        method, file_key = method_map.get(msg.media_type, ("sendDocument", "document"))

        # Try reading from URL (R2/S3) or local path
        file_url = msg.media_file.url
        if file_url.startswith("http"):
            # Download from R2 first, then send to Telegram
            file_data = req.get(file_url, timeout=30).content
            req.post(
                f"https://api.telegram.org/bot{token}/{method}",
                data={"chat_id": chat_id, "caption": msg.content or ""},
                files={file_key: (msg.media_filename, file_data)},
                timeout=30,
            )
        else:
            # Local file
            with open(msg.media_file.path, "rb") as f:
                req.post(
                    f"https://api.telegram.org/bot{token}/{method}",
                    data={"chat_id": chat_id, "caption": msg.content or ""},
                    files={file_key: (msg.media_filename, f)},
                    timeout=30,
                )
    except Exception as e:
        print(f"Send media to telegram failed: {e}")


def _broadcast_ticket_update(ticket):
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)("agents", {"type": "ticket_update", "ticket": TicketListSerializer(ticket).data})
    except Exception:
        pass


def _broadcast_message(ticket, message):
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(f"ticket_{ticket.id}", {"type": "new_message", "message": MessageSerializer(message).data})
    except Exception:
        pass
