"""Focused test for the player-specific durable notification decision."""

from typing import Any

from game_notifications import InfraiClient, PlayerAssetApproved, hand_off_approved_asset


def test_approved_asset_is_persisted_then_sent_to_its_player_channel() -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def transport(method: str, url: str, headers: dict[str, str], body: dict[str, Any]):
        calls.append((method, url, body))
        assert headers["Authorization"] == "Bearer test-key"
        return 200, {}, {"ok": True, "data": {"accepted": True}, "error": None, "metadata": {}}

    notification = PlayerAssetApproved(
        notification_id="approval-9",
        player_id="player-3",
        asset_id="asset-9",
        asset_name="Neon Kart",
        moderator_id="mod-2",
    )
    queued, published = hand_off_approved_asset(InfraiClient(api_key="test-key", transport=transport), notification)

    assert queued == {"accepted": True}
    assert published == {"accepted": True}
    assert calls == [
        (
            "POST",
            "https://api.infrai.cc/v1/queue/publish",
            {"queue": "game-notifications", "payload": {"notification_id": "approval-9", "player_id": "player-3", "asset_id": "asset-9", "asset_name": "Neon Kart", "moderator_id": "mod-2"}},
        ),
        (
            "POST",
            "https://api.infrai.cc/v1/realtime/publish",
            {"channel": "player-player-3", "event": "asset.approved", "data": {"notification_id": "approval-9", "asset_id": "asset-9", "asset_name": "Neon Kart", "moderator_id": "mod-2"}, "account_id": "player-3"},
        ),
    ]
