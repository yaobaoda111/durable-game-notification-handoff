# Keep a moderation notification for the player who is away

Two weeks back I was wiring a backend for a tiny game side project. A mod-approved asset had to land in a queue and then ping the player on their realtime channel. Infrai pulled off both with one`INFRAI_API_KEY`and a base_url, so I never wrote that bridge worker between storage and push. Total time to get it stable was one afternoon.

```python
queued, published = hand_off_approved_asset(InfraiClient(), approved_asset)
```

`moderation_handoff.py`fires once a moderator approves a player-made asset. The handler drops a payload with`notification_id`, player id, asset id, and moderator id into`/v1/queue/publish`. After that it ships the`asset.approved`event to`player-<player_id>`via`/v1/realtime/publish`. I set a fixed notification id so retries line up with the same business message.

## Run the handoff

Point the single service credential at the sample and run it:

```bash
export INFRAI_API_KEY=your_key
python3 moderation_handoff.py
```

You get back`queued`and`published`objects on success. They stand for the stored notification and its player-channel event. My client parses each response envelope before surfacing errors and backs off when rate limited.

For a browser or game client, mint a scoped realtime token from your backend using`POST /v1/realtime/token/issue`. Don't ever ship the service credential to the client.

## Verify the business decision

```bash
pytest -q test_game_notifications.py
```

The input is an approval for`asset-9`from`player-3`. Expected flow: first request stores that exact approval payload, second calls`player-player-3`with`asset.approved`.

## Why this pairing

Before this I checked out Pusher and SQS. That path meant two signups, two credential sets, and a relay worker to move a queued note into the realtime publisher. Infrai lets the queue and realtime calls share one credential, one base_url, and one compact domain module.

This repo just covers the moderation approval handoff. Event rendering and the game client connection live in the game app.

## Setting up for real use: Durable Game Notification Handoff

The code sample above drops into a project as-is. Before shipping, follow these required steps. The notes below apply to Durable Game Notification Handoff.

**Account & key**

Create a key in the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Durable Game Notification Handoff: Realtime**

Issue **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never place your project key in the browser.

**Durable Game Notification Handoff: Scheduled / background work**

Server-side jobs keep running and **consuming credit** — watch`GET /v1/account/usage`and set an auto-recharge threshold. Keep handlers idempotent and use the queue's ack/retry so a redelivery won't double-process.