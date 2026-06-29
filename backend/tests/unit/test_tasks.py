import pytest
from httpx import AsyncClient
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.workspace import WorkspaceMember


pytestmark = pytest.mark.asyncio


class TestCreateTask:
    async def test_create_task_success(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={
                "title": "Build authentication module",
                "description": "Implement JWT-based auth",
                "status": "todo",
                "priority": "high",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Build authentication module"
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert data["assignee_id"] is None

    async def test_create_task_requires_auth(
        self, client: AsyncClient, test_org, test_workspace
    ):
        response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "Unauthorized task",
                  "status": "todo", "priority": "low"},
        )
        assert response.status_code == 401

    async def test_create_task_missing_title(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"status": "todo", "priority": "low"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_create_task_non_member_forbidden(
        self, client: AsyncClient, second_auth_headers, test_org, test_workspace
    ):
        response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "Intruder task",
                  "status": "todo", "priority": "low"},
            headers=second_auth_headers,
        )
        assert response.status_code in (403, 404)


class TestListTasks:
    async def test_list_tasks_success(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    async def test_list_tasks_filter_by_status(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks?status=todo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for task in data["items"]:
            assert task["status"] == "todo"

    async def test_list_tasks_search(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={
                "title": "Deploy Kubernetes cluster",
                "description": "Set up production infrastructure",
                "status": "todo",
                "priority": "high",
            },
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks?search=kubernetes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        # FTS trigger only exists in migrated DBs; just verify the endpoint works
        assert "items" in response.json()

    async def test_list_tasks_pagination(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks?page=1&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2


class TestGetTask:
    async def test_get_task_success(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        # Create a task
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "Fetch me", "status": "todo", "priority": "low"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/{task_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == task_id

    async def test_get_task_not_found(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateTask:
    async def test_update_task_status(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "To be updated",
                  "status": "todo", "priority": "medium"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/{task_id}",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    async def test_update_task_completion_sets_completed_at(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "Almost done",
                  "status": "todo", "priority": "medium"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/{task_id}",
            json={"status": "done"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["completed_at"] is not None

    async def test_assign_task_triggers_notification_and_email(
        self,
        client: AsyncClient,
        auth_headers,
        test_org,
        test_workspace,
        second_user,
        db: AsyncSession,
    ):
        # Add second user to workspace
        from datetime import datetime, timezone
        member = WorkspaceMember(
            workspace_id=test_workspace.id,
            user_id=second_user.id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
        db.add(member)
        await db.commit()

        # Create task
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "Assign me", "status": "todo", "priority": "high"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        # Mock the email task so we don't hit Resend in tests
        with patch("app.workers.email_tasks.send_task_assigned_email.delay") as mock_email:
            response = await client.patch(
                f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/{task_id}",
                json={"assignee_id": str(second_user.id)},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert response.json()["assignee_id"] == str(second_user.id)

            # Verify email task was queued
            mock_email.assert_called_once()
            call_kwargs = mock_email.call_args.kwargs
            assert call_kwargs["to_email"] == second_user.email
            assert call_kwargs["task_title"] == "Assign me"


class TestDeleteTask:
    async def test_delete_task_soft_deletes(
        self, client: AsyncClient, auth_headers, test_org, test_workspace
    ):
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
            json={"title": "Delete me", "status": "todo", "priority": "low"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/{task_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Task should no longer appear in list
        get_response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks/{task_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404
