import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Ticket, Message


class AgentConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket for agent dashboard.
    - Joins 'agents' group to receive ticket updates.
    - Can join specific ticket rooms for live chat.
    """

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Join the agents broadcast group
        await self.channel_layer.group_add("agents", self.channel_name)
        await self.accept()

        # Mark user online
        await self._set_online(True)

    async def disconnect(self, code):
        await self.channel_layer.group_discard("agents", self.channel_name)

        # Leave any ticket rooms
        if hasattr(self, "current_ticket_room"):
            await self.channel_layer.group_discard(self.current_ticket_room, self.channel_name)

        if self.user and self.user.is_authenticated:
            await self._set_online(False)

    async def receive_json(self, content):
        action = content.get("action")

        if action == "join_ticket":
            ticket_id = content.get("ticket_id")
            if ticket_id:
                # Leave previous room if any
                if hasattr(self, "current_ticket_room"):
                    await self.channel_layer.group_discard(self.current_ticket_room, self.channel_name)
                # Join new ticket room
                self.current_ticket_room = f"ticket_{ticket_id}"
                await self.channel_layer.group_add(self.current_ticket_room, self.channel_name)
                await self.send_json({"type": "joined_ticket", "ticket_id": ticket_id})

        elif action == "leave_ticket":
            if hasattr(self, "current_ticket_room"):
                await self.channel_layer.group_discard(self.current_ticket_room, self.channel_name)
                del self.current_ticket_room

        elif action == "send_message":
            ticket_id = content.get("ticket_id")
            text = content.get("content", "").strip()
            is_internal = content.get("is_internal_note", False)

            if ticket_id and text:
                msg = await self._create_message(ticket_id, text, is_internal)
                if msg:
                    # Broadcast to ticket room
                    await self.channel_layer.group_send(
                        f"ticket_{ticket_id}",
                        {
                            "type": "new_message",
                            "message": msg,
                        },
                    )

        elif action == "typing":
            ticket_id = content.get("ticket_id")
            if ticket_id:
                await self.channel_layer.group_send(
                    f"ticket_{ticket_id}",
                    {
                        "type": "agent_typing",
                        "agent_id": str(self.user.id),
                        "agent_name": self.user.get_full_name() or self.user.username,
                    },
                )

    # ── Group message handlers ────────────────────────────────────────────

    async def ticket_update(self, event):
        await self.send_json({
            "type": "ticket_update",
            "ticket": event["ticket"],
        })

    async def new_message(self, event):
        await self.send_json({
            "type": "new_message",
            "message": event["message"],
        })

    async def agent_typing(self, event):
        await self.send_json({
            "type": "agent_typing",
            "agent_id": event["agent_id"],
            "agent_name": event["agent_name"],
        })

    # ── DB helpers ────────────────────────────────────────────────────────

    @database_sync_to_async
    def _set_online(self, is_online):
        self.user.is_online = is_online
        self.user.save(update_fields=["is_online"])

    @database_sync_to_async
    def _create_message(self, ticket_id, content, is_internal):
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return None

        # Only assigned agent or super admin can send messages
        if not self.user.is_super_admin and ticket.assigned_agent != self.user:
            return None

        msg = Message.objects.create(
            ticket=ticket,
            sender_type=Message.SenderType.AGENT,
            sender_agent=self.user,
            content=content,
            is_internal_note=is_internal,
        )

        # Update ticket status to in_progress if it was just assigned
        if ticket.status == Ticket.Status.ASSIGNED:
            ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save(update_fields=["status", "updated_at"])

        # Send to user via Telegram (unless internal note)
        if not is_internal:
            from .views import _notify_user_via_telegram
            _notify_user_via_telegram(ticket.telegram_chat_id, content)

        return {
            "id": str(msg.id),
            "ticket": str(ticket_id),
            "sender_type": "agent",
            "sender_name": self.user.get_full_name() or self.user.username,
            "content": content,
            "is_internal_note": is_internal,
            "created_at": msg.created_at.isoformat(),
        }
