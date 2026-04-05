from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Service, Company, Ticket, Message, BotConfig, TicketTransferLog


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("Account disabled")
        if user.role not in ("super_admin", "agent"):
            raise serializers.ValidationError("Not authorized for agent panel")
        return {"user": user}


# ── Users ─────────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    allowed_companies = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Company.objects.all(), required=False
    )
    active_ticket_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "allowed_companies", "is_online", "is_active",
            "max_concurrent_tickets", "active_ticket_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_active_ticket_count(self, obj):
        return obj.assigned_tickets.filter(status__in=["assigned", "in_progress"]).count()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    allowed_companies = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Company.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = [
            "username", "email", "password", "first_name", "last_name",
            "role", "allowed_companies", "max_concurrent_tickets",
        ]

    def create(self, validated_data):
        companies = validated_data.pop("allowed_companies", [])
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if companies:
            user.allowed_companies.set(companies)
        return user


# ── Services & Companies ──────────────────────────────────────────────────────

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id", "service", "name", "icon", "display_order",
            "is_active", "form_schema", "welcome_message",
            "ticket_created_message", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ServiceSerializer(serializers.ModelSerializer):
    companies = CompanySerializer(many=True, read_only=True)
    company_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id", "name", "icon", "display_order", "is_active",
            "companies", "company_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_company_count(self, obj):
        return obj.companies.filter(is_active=True).count()


class ServiceListSerializer(serializers.ModelSerializer):
    company_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ["id", "name", "icon", "display_order", "is_active", "company_count"]

    def get_company_count(self, obj):
        return obj.companies.filter(is_active=True).count()


# ── Tickets ───────────────────────────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id", "ticket", "sender_type", "sender_agent",
            "sender_name", "content", "is_internal_note",
            "media_type", "media_url", "media_filename", "media_size",
            "created_at",
        ]
        read_only_fields = ["id", "ticket", "sender_type", "sender_agent", "created_at"]

    def get_sender_name(self, obj):
        if obj.sender_type == "agent" and obj.sender_agent:
            return obj.sender_agent.get_full_name() or obj.sender_agent.username
        if obj.sender_type == "user":
            return "Customer"
        return "System"

    def get_media_url(self, obj):
        if obj.media_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.media_file.url)
            return obj.media_file.url
        return None


class TicketSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    assigned_agent_name = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id", "ticket_number", "service", "service_name",
            "company", "company_name", "form_data",
            "assigned_agent", "assigned_agent_name",
            "status", "priority",
            "message_count", "latest_message",
            "created_at", "updated_at", "assigned_at", "resolved_at",
        ]
        read_only_fields = ["id", "ticket_number", "created_at", "updated_at"]

    def get_assigned_agent_name(self, obj):
        return (obj.assigned_agent.get_full_name() or obj.assigned_agent.username) if obj.assigned_agent else None

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_latest_message(self, obj):
        msg = obj.messages.exclude(is_internal_note=True).last()
        return MessageSerializer(msg).data if msg else None


class TicketSuperAdminSerializer(TicketSerializer):
    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + [
            "telegram_user_id", "telegram_chat_id",
            "telegram_username", "telegram_first_name",
        ]


class TicketListSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    assigned_agent_name = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id", "ticket_number", "service_name", "company_name",
            "status", "priority", "assigned_agent", "assigned_agent_name",
            "created_at", "updated_at",
        ]

    def get_assigned_agent_name(self, obj):
        return (obj.assigned_agent.get_full_name() or obj.assigned_agent.username) if obj.assigned_agent else None


# ── Transfer ──────────────────────────────────────────────────────────────────

class TicketTransferSerializer(serializers.Serializer):
    to_agent_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, default="")


class TransferLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketTransferLog
        fields = ["id", "ticket", "from_agent", "to_agent", "reason", "created_at"]


# ── Bot Config ────────────────────────────────────────────────────────────────

class BotConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotConfig
        fields = [
            "id", "name", "bot_username", "status", "priority",
            "last_health_check", "last_error", "is_webhook_set", "created_at",
        ]
        read_only_fields = ["id", "created_at", "last_health_check"]
