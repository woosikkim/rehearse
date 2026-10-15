# Demo: mock server

A tiny shop API on your own machine, and documentation that is wrong about it. The task is to build a script that reads it.

## The API (as documented)

- `GET http://localhost:8766/api/items` returns the items.
- Each item has a `name` and a `price` in dollars.

## Before the session

Start the server in a separate terminal. It blocks, so it must not be run from the agent's own shell.

```
cd demos/mock-server && python3 server.py
```

## Try it

```
cd demos/mock-server && claude --plugin-dir ../..
```

Prompt:

```
rehearse: build a script that lists item names and prices from the local API
```

## Not in the plugin eval

The eval runs the agent's shell in a sandbox that refuses connections to this server, so this demo is run by hand only (first eval run, 2026-10-15).

## Expected story

The documentation above is wrong on purpose. The server really answers on `/api/v1/items`, and each item has `price_cents` (1999), not `price`. An agent that builds from the documentation writes a script that gets a 404. An agent that looks first fetches the real address, sees the real fields, and registers an ending built from what the server answered:

| Name         | Price   |
|--------------|---------|
| Blue Mug     | 19.99   |
| Sticker Pack | 5.49    |
| Desk Lamp    | 120.00  |

A good run's ending names `/api/v1/items` and `price_cents`, and its report says the documentation was wrong.
