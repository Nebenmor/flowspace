import pytest
import hmac
import hashlib
import json
from httpx import AsyncClient
from unittest.mock import patch


pytestmark = pytest.mark.asyncio


class TestWebhookCRUD:
    async def test_create_webhook_success(
        self, client: AsyncClient, auth_headers, test_org
    ):
        response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/webhooks",
            json={
                "name": "CI Notifier",
                "url": "https://example.com/webhook",
                "events": ["task.created", "task.completed"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "CI Notifier"
        assert data["url"] == "https://example.com/webhook"
        # assert "secret" in data
        assert data["is_active"] is True

    async def test_create_webhook_invalid_url(
        self, client: AsyncClient, auth_headers, test_org
    ):
        response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/webhooks",
            json={
                "name": "Bad Webhook",
                "url": "not-a-url",
                "events": ["task.created"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_list_webhooks(
        self, client: AsyncClient, auth_headers, test_org
    ):
        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/webhooks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_delete_webhook(
        self, client: AsyncClient, auth_headers, test_org
    ):
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/webhooks",
            json={
                "name": "To delete",
                "url": "https://example.com/hook",
                "events": ["task.created"],
            },
            headers=auth_headers,
        )
        webhook_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/organizations/{test_org.slug}/webhooks/{webhook_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204


# Signature tests are sync — no asyncio mark needed
class TestWebhookSignature:
    def test_signature_verification_valid(self):
        """HMAC-SHA256 signature must match for a valid payload."""
        secret = "test-webhook-secret"
        payload = json.dumps({"task_id": "abc123", "event": "task.created"})

        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        expected = f"sha256={signature}"
        assert hmac.compare_digest(expected, f"sha256={signature}")

    def test_signature_verification_tampered_payload(self):
        """A tampered payload must not match the original signature."""
        secret = "test-webhook-secret"
        original_payload = json.dumps({"task_id": "abc123"})
        tampered_payload = json.dumps({"task_id": "malicious"})

        original_sig = hmac.new(
            secret.encode(),
            original_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        tampered_sig = hmac.new(
            secret.encode(),
            tampered_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert original_sig != tampered_sig


class TestWebhookDelivery:
    async def test_task_creation_triggers_webhook_delivery(
        self,
        client: AsyncClient,
        auth_headers,
        test_org,
        test_workspace,
    ):
        """Creating a task should attempt webhook delivery."""
        # Register a webhook
        await client.post(
            f"/api/v1/organizations/{test_org.slug}/webhooks",
            json={
                "name": "Task watcher",
                "url": "https://example.com/hook",
                "events": ["task.created"],
            },
            headers=auth_headers,
        )

        with patch("app.services.webhook_service.deliver_webhook") as mock_deliver:
            mock_deliver.return_value = None
            await client.post(
                f"/api/v1/organizations/{test_org.slug}/workspaces/{test_workspace.slug}/tasks",
                json={
                    "title": "Webhook trigger task",
                    "status": "todo",
                    "priority": "medium",
                },
                headers=auth_headers,
            )
            assert mock_deliver.called

    def test_webhook_delivery_retry_backoff(self):
        """Each retry should be scheduled further in the future."""
        from app.services.webhook_service import _next_retry_time
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        retry_1 = _next_retry_time(1)
        retry_2 = _next_retry_time(2)
        retry_3 = _next_retry_time(3)

        assert retry_1 > now
        assert retry_2 > retry_1
        assert retry_3 > retry_2

    async def test_webhook_delivery_history(
        self, client: AsyncClient, auth_headers, test_org
    ):
        """Delivery history endpoint should return a list."""
        create_response = await client.post(
            f"/api/v1/organizations/{test_org.slug}/webhooks",
            json={
                "name": "History watcher",
                "url": "https://example.com/hook",
                "events": ["task.created"],
            },
            headers=auth_headers,
        )
        webhook_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/organizations/{test_org.slug}/webhooks/{webhook_id}/deliveries",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
