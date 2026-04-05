import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        AGENT = "agent", "Agent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)

    # Granular access: agent can be assigned specific companies
    allowed_companies = models.ManyToManyField("Company", blank=True, related_name="agents")

    is_online = models.BooleanField(default=False)
    max_concurrent_tickets = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    def can_access_ticket(self, ticket):
        if self.is_super_admin:
            return True
        return self.allowed_companies.filter(id=ticket.company_id).exists()

    def get_allowed_service_ids(self):
        """Get unique service IDs from allowed companies."""
        return list(self.allowed_companies.values_list("service_id", flat=True).distinct())

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=10, default="📋")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.icon} {self.name}"


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, default="🏢")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Dynamic form schema
    # [{"key": "from_city", "label": "From city?", "type": "text", "required": true}, ...]
    form_schema = models.JSONField(default=list)

    # Custom bot messages for this company (optional overrides)
    welcome_message = models.TextField(blank=True, default="", help_text="Custom greeting when user selects this company")
    ticket_created_message = models.TextField(blank=True, default="", help_text="Custom message after ticket creation")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        unique_together = ["service", "name"]

    def __str__(self):
        return f"{self.name} ({self.service.name})"


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)

    telegram_user_id = models.BigIntegerField()
    telegram_chat_id = models.BigIntegerField()
    telegram_username = models.CharField(max_length=200, blank=True, default="")
    telegram_first_name = models.CharField(max_length=200, blank=True, default="")

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="tickets")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="tickets")
    form_data = models.JSONField(default=dict)

    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    bot_token_hash = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["telegram_user_id"]),
            models.Index(fields=["assigned_agent", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            prefix = self.service.name[:3].upper()
            last = Ticket.objects.filter(ticket_number__startswith=prefix).count()
            self.ticket_number = f"{prefix}-{last + 1:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.company.name} ({self.get_status_display()})"


class Message(models.Model):
    class SenderType(models.TextChoices):
        USER = "user", "User"
        AGENT = "agent", "Agent"
        SYSTEM = "system", "System"

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        DOCUMENT = "document", "Document"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=10, choices=SenderType.choices)
    sender_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_messages")
    content = models.TextField(blank=True, default="")
    is_internal_note = models.BooleanField(default=False)

    media_type = models.CharField(max_length=10, choices=MediaType.choices, blank=True, default="")
    media_file = models.FileField(upload_to="chat_media/%Y/%m/%d/", blank=True, default="")
    media_filename = models.CharField(max_length=500, blank=True, default="")
    media_size = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def has_media(self):
        return bool(self.media_file)

    @property
    def media_url(self):
        return self.media_file.url if self.media_file else None

    def __str__(self):
        prefix = f"[{self.get_sender_type_display()}]"
        if self.has_media:
            return f"{prefix} [{self.media_type}] {self.media_filename}"
        return f"{prefix} {self.content[:50]}"


class BotConfig(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        STANDBY = "standby", "Standby"
        BANNED = "banned", "Banned"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=200, unique=True)
    bot_username = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STANDBY)
    priority = models.PositiveIntegerField(default=0)
    last_health_check = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    is_webhook_set = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @classmethod
    def get_active_bot(cls):
        active = cls.objects.filter(status=cls.Status.ACTIVE).first()
        if active:
            return active
        standby = cls.objects.filter(status=cls.Status.STANDBY).first()
        if standby:
            standby.status = cls.Status.ACTIVE
            standby.save(update_fields=["status"])
            return standby
        return None


class TicketTransferLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="transfer_logs")
    from_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="transfers_out")
    to_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="transfers_in")
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
