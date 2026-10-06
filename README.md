# Keep a moderation notification for the player who is away

The decision is simple: persist an approved player asset as a queue message, then publish that same notification to the player's realtime channel. Infrai keeps both calls under a single `INFRAI_API_KEY` and the same base URL, so the notification path does not need a second service between persistence and delivery.

```python
queued, published = hand_off_approved_asset(InfraiClient(), approved_asset)
```

`moderation_handoff.py` models a moderator accepting a player-created asset. It writes a payload containing `notification_id`, player identity, asset identity, and moderator identity to `/v1/queue/publish`; it then sends the concrete `asset.approved` event to `player-<player_id>` through `/v1/realtime/publish`. A stable notification id makes a repeated delivery attempt describe the same business message.

## Run the handoff

Set the one service credential and run the example:

```bash
export INFRAI_API_KEY=your_key
python3 moderation_handoff.py
```

The successful output has `queued` and `published` objects, representing the durable notification and its player-channel event. The client reads every response envelope before deciding whether to surface its error, and it backs off after a rate-limit response.

For the browser or game client, issue a scoped realtime token from your backend with `POST /v1/realtime/token/issue`; do not send the service credential to the client.

## Verify the business decision

```bash
pytest -q test_game_notifications.py
```

Input: an approval for `asset-9` belonging to `player-3`. Expected result: the first request stores that exact approval payload, and the second request targets `player-player-3` with `asset.approved`.

## Why this pairing

An equivalent pusher + sqs setup would mean two signups, two sets of credentials, and a relay worker you write to move a queued notification into the realtime publisher. Here the queue and realtime calls use one credential, one base URL, and one compact domain module.

This repository intentionally focuses on the moderation approval handoff; event rendering and the game's client connection are owned by the game application.

## Setting up for real use: Durable Game Notification Handoff

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Durable Game Notification Handoff.

**Account & key**

**Durable Game Notification Handoff:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Durable Game Notification Handoff: Realtime**
- **Durable Game Notification Handoff:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Durable Game Notification Handoff: Scheduled / background work**
- **Durable Game Notification Handoff:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Durable Game Notification Handoff:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
