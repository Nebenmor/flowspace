import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_db, get_current_user_ws
from app.db.models.workspace import Workspace, WorkspaceMember
from app.db.models.organization import Organization
from app.websockets.manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{org_slug}/{workspace_slug}")
async def websocket_endpoint(
    websocket: WebSocket,
    org_slug: str,
    workspace_slug: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # Authenticate user
    try:
        current_user = await get_current_user_ws(websocket, token, db)
    except Exception:
        await websocket.close(code=1008)
        return

    # Verify workspace exists and user is a member
    result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        await websocket.close(code=1008)
        return

    result = await db.execute(
        select(Workspace).where(
            Workspace.org_id == org.id,
            Workspace.slug == workspace_slug,
            Workspace.is_archived == False,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        await websocket.close(code=1008)
        return

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        await websocket.close(code=1008)
        return

    workspace_id = str(workspace.id)
    user_id = str(current_user.id)

    # Connect to room
    await manager.connect(websocket, workspace_id, user_id)

    try:
        while True:
            # Listen for messages from this client
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
                event = message.get("event")
                data = message.get("data", {})
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "event": "error",
                    "data": {"message": "Invalid JSON"},
                }))
                continue

            # Handle client-sent events
            if event == "presence.update":
                # Client tells us what they're currently viewing
                viewing = data.get("viewing", "workspace")
                manager.update_presence(user_id, workspace_id, viewing)

                # Broadcast updated presence to everyone else
                await manager.broadcast_to_workspace(
                    workspace_id=workspace_id,
                    event="presence.updated",
                    data={
                        "user_id": user_id,
                        "viewing": viewing,
                    },
                    exclude_user=user_id,
                )

            elif event == "ping":
                # Heartbeat — keep connection alive
                await websocket.send_text(json.dumps({"event": "pong"}))

    except WebSocketDisconnect:
        await manager.disconnect(workspace_id, user_id)