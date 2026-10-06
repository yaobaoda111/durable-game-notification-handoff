"""Run the observable moderation-to-player notification handoff."""

import json

from game_notifications import InfraiClient, PlayerAssetApproved, hand_off_approved_asset


def main() -> None:
    approved_asset = PlayerAssetApproved(
        notification_id="approval-asset-42",
        player_id="player-17",
        asset_id="asset-42",
        asset_name="Sky Harbor",
        moderator_id="mod-8",
    )
    queued, published = hand_off_approved_asset(InfraiClient(), approved_asset)
    print(json.dumps({"queued": queued, "published": published}, indent=2))


if __name__ == "__main__":
    main()
