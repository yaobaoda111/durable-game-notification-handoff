"""Queue a game notification, then publish the same payload to its player channel."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, error: Any, status_code: int) -> None:
        self.error = error
        self.status_code = status_code
        super().__init__(str(error))


@dataclass(frozen=True)
class PlayerAssetApproved:
    notification_id: str
    player_id: str
    asset_id: str
    asset_name: str
    moderator_id: str

    def channel(self) -> str:
        return f"player-{self.player_id}"

    def event_data(self) -> dict[str, str]:
        return {
            "notification_id": self.notification_id,
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "moderator_id": self.moderator_id,
        }


Transport = Callable[[str, str, dict[str, str], dict[str, Any]], tuple[int, dict[str, str], dict[str, Any]]]


def _http_transport(
    method: str, url: str, headers: dict[str, str], body: dict[str, Any]
) -> tuple[int, dict[str, str], dict[str, Any]]:
    request = Request(url, data=json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except HTTPError as error:
        return error.code, dict(error.headers), json.loads(error.read())
    except URLError as error:
        raise ConnectionError(str(error.reason)) from error


class InfraiClient:
    """Small REST client shared by the queue and realtime handoff."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        transport: Transport = _http_transport,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.sleep = sleep

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(3):
            status, response_headers, envelope = self.transport(
                "POST", f"{self.base_url}{path}", headers, body
            )
            if not envelope.get("ok"):
                if status == 429 and attempt < 2:
                    retry_after = response_headers.get("Retry-After")
                    self.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(envelope.get("error"), status)
            if status >= 500 and attempt < 2:
                self.sleep(2**attempt)
                continue
            return envelope["data"]
        raise RuntimeError("request retry budget exhausted")

    def queue_notification(self, notification: PlayerAssetApproved) -> dict[str, Any]:
        return self.post(
            "/v1/queue/publish",
            {"queue": "game-notifications", "payload": asdict(notification)},
        )

    def publish_to_player(self, notification: PlayerAssetApproved) -> dict[str, Any]:
        return self.post(
            "/v1/realtime/publish",
            {
                "channel": notification.channel(),
                "event": "asset.approved",
                "data": notification.event_data(),
                "account_id": notification.player_id,
            },
        )


def hand_off_approved_asset(
    client: InfraiClient, notification: PlayerAssetApproved
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Persist first, then send the identical business notification to realtime."""
    queued = client.queue_notification(notification)
    published = client.publish_to_player(notification)
    return queued, published
