import json
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # workspace_id -> {user_id -> WebSocket}
        self.rooms: dict[str, dict[str, WebSocket]] = {}

        # user_id -> {workspace_id -> what they're viewing}
        self.presence: dict[str, dict[str, str]] = {}

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        workspace_id: str,
        user_id: str,
    ) -> None:
        await websocket.accept()

        if workspace_id not in self.rooms:
            self.rooms[workspace_id] = {}

        self.rooms[workspace_id][user_id] = websocket

        if user_id not in self.presence:
            self.presence[user_id] = {}

        self.presence[user_id][workspace_id] = "workspace"

        # Notify others in the room that this user came online
        await self.broadcast_to_workspace(
            workspace_id=workspace_id,
            event="user.joined",
            data={"user_id": user_id},
            exclude_user=user_id,
        )

        # Send current presence list to the newly connected user
        await self.send_to_user(
            user_id=user_id,
            workspace_id=workspace_id,
            event="presence.sync",
            data={"online_users": self.get_online_users(workspace_id)},
        )

    async def disconnect(
        self,
        workspace_id: str,
        user_id: str,
    ) -> None:
        if workspace_id in self.rooms:
            self.rooms[workspace_id].pop(user_id, None)
            if not self.rooms[workspace_id]:
                del self.rooms[workspace_id]

        if user_id in self.presence:
            self.presence[user_id].pop(workspace_id, None)
            if not self.presence[user_id]:
                del self.presence[user_id]

        # Notify others this user left
        await self.broadcast_to_workspace(
            workspace_id=workspace_id,
            event="user.left",
            data={"user_id": user_id},
        )

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def broadcast_to_workspace(
        self,
        workspace_id: str,
        event: str,
        data: dict[str, Any],
        exclude_user: str | None = None,
    ) -> None:
        """Send an event to all connected users in a workspace."""
        if workspace_id not in self.rooms:
            return

        message = _build_message(event, data)
        disconnected = []

        for user_id, websocket in self.rooms[workspace_id].items():
            if user_id == exclude_user:
                continue
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(user_id)

        # Clean up broken connections
        for user_id in disconnected:
            await self.disconnect(workspace_id, user_id)

    async def send_to_user(
        self,
        user_id: str,
        workspace_id: str,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Send an event to a specific user in a workspace."""
        if workspace_id not in self.rooms:
            return
        websocket = self.rooms[workspace_id].get(user_id)
        if websocket:
            try:
                await websocket.send_text(_build_message(event, data))
            except Exception:
                await self.disconnect(workspace_id, user_id)

    # ── Presence ──────────────────────────────────────────────────────────────

    def update_presence(
        self,
        user_id: str,
        workspace_id: str,
        viewing: str,
    ) -> None:
        """Update what a user is currently viewing e.g. task UUID or 'workspace'."""
        if user_id in self.presence:
            self.presence[user_id][workspace_id] = viewing

    def get_online_users(self, workspace_id: str) -> list[dict]:
        """Return list of online users and what they're viewing."""
        if workspace_id not in self.rooms:
            return []

        online = []
        for user_id in self.rooms[workspace_id]:
            viewing = "workspace"
            if user_id in self.presence:
                viewing = self.presence[user_id].get(workspace_id, "workspace")
            online.append({
                "user_id": user_id,
                "viewing": viewing,
            })
        return online

    def is_user_online(self, workspace_id: str, user_id: str) -> bool:
        return (
            workspace_id in self.rooms
            and user_id in self.rooms[workspace_id]
        )


def _build_message(event: str, data: dict[str, Any]) -> str:
    """Standardize all WebSocket message format."""
    return json.dumps({
        "event": event,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# Singleton instance — shared across the entire application
manager = ConnectionManager()