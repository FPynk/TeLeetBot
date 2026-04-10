# Discord Startup Cancellation Bug

## Summary

The Discord bot is successfully connecting, but the application cancels its own long-running Discord task immediately after the client becomes ready.

That cancellation propagates out of `asyncio.gather(...)`, the process exits with `asyncio.exceptions.CancelledError`, and Docker restarts the container.

This is why the logs show:

```text
[Discord] synced 10 global commands
[Discord] connected as TeLeetBot#7802
...
asyncio.exceptions.CancelledError
Bot running
```

The first three lines prove Discord startup succeeded. The later `CancelledError` is caused by our own readiness helper.

## Relevant Code

### `src/main.py`

```python
async def main():
    db.init()

    tasks = [asyncio.create_task(start_telegram(), name="telegram-client")]
    if discord_enabled():
        discord_task = asyncio.create_task(start_discord(), name="discord-client")
        try:
            # Do not start the shared poller until Discord can actually send messages.
            await wait_for_discord_ready(discord_task)
        except Exception as exc:
            print(
                "[Discord] startup failed - continuing without Discord for this run: "
                f"{type(exc).__name__}: {exc}"
            )
            if not discord_task.done():
                discord_task.cancel()
            await asyncio.gather(discord_task, return_exceptions=True)
            else:
                tasks.append(discord_task)

    await start_schedulers()
    start_poller()

    await asyncio.gather(*tasks)
```

Important points:

- `discord_task` is the real long-running Discord client task.
- If readiness succeeds, that task is added to `tasks`.
- `asyncio.gather(*tasks)` later awaits it for the life of the process.

### `src/discord_bot.py`

```python
async def start_discord():
    if discord_client is None:
        return
    await discord_client.start(DISCORD_BOT_TOKEN)


async def wait_for_discord_ready(discord_task: asyncio.Task | None):
    if discord_client is None or discord_task is None:
        return

    ready_waiter = asyncio.create_task(discord_client.wait_until_ready())
    done, pending = await asyncio.wait(
        {ready_waiter, discord_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    if ready_waiter in done:
        await ready_waiter
        return

    await discord_task
    raise RuntimeError("Discord client exited before becoming ready.")
```

The bug is in this block:

```python
done, pending = await asyncio.wait(
    {ready_waiter, discord_task},
    return_when=asyncio.FIRST_COMPLETED,
)

for task in pending:
    task.cancel()
```

## What Actually Happens At Runtime

### Normal intended sequence

The intended flow was:

1. Start the real Discord task with `start_discord()`
2. Wait until the Discord client is ready
3. Start the scheduler and poller only after Discord can send messages
4. Keep the Discord task alive forever

### Actual sequence

What actually happens is:

1. `main()` creates `discord_task`
2. `wait_for_discord_ready(discord_task)` creates a second task called `ready_waiter`
3. `ready_waiter` waits for `discord_client.wait_until_ready()`
4. Discord logs in successfully
5. `ready_waiter` finishes first
6. `asyncio.wait(..., FIRST_COMPLETED)` returns:
   - `done = {ready_waiter}`
   - `pending = {discord_task}`
7. The code then cancels every pending task
8. That means it cancels the real long-running `discord_task`
9. `wait_for_discord_ready()` returns as if startup succeeded
10. `main()` appends the now-cancelled `discord_task` to `tasks`
11. `await asyncio.gather(*tasks)` sees the cancelled Discord task
12. The process exits with `asyncio.exceptions.CancelledError`

This is the key mistake:

```python
for task in pending:
    task.cancel()
```

On the successful path, the only pending task is the real Discord bot task. So the code kills the bot immediately after it becomes ready.

## Why The Logs Look Confusing

The logs make it look like Discord succeeded and then randomly died:

```text
[Discord] synced 10 global commands
[Discord] connected as TeLeetBot#7802
```

That part is true. Discord *did* succeed.

The failure happens **after** readiness, when the helper cancels the still-running Discord client task.

So this is not:

- a bad bot token
- a bad application ID
- a gateway permission problem
- a slash command sync problem

It is a self-inflicted cancellation bug in the startup orchestration.

## Why `CancelledError` Escapes

The traceback shows:

```text
File "/app/src/main.py", line 36, in main
    await asyncio.gather(*tasks)
...
File "/app/src/discord_bot.py", line 46, in start_discord
    await discord_client.start(DISCORD_BOT_TOKEN)
...
asyncio.exceptions.CancelledError
```

That means:

- `discord_task` was cancelled while `discord_client.start(...)` was still running
- the cancellation surfaced when `main()` later awaited the task inside `asyncio.gather(...)`

The `try/except Exception` around `wait_for_discord_ready(...)` in `main()` does not help here, because the cancellation does not happen as a normal startup exception inside that block. Readiness returned successfully first, and the cancelled task is only observed later during the final `gather(...)`.

## Why Docker Starts The Container Again

The container restarts because `docker-compose.yml` uses:

```yaml
restart: unless-stopped
```

So the sequence is:

1. app exits due to `CancelledError`
2. Docker treats that as container failure
3. Docker restarts the container
4. logs begin again with:

```text
Bot running
```

## Conceptual Fix

The helper should only cancel the temporary waiter task when Discord exits first.

It should **not** cancel `discord_task` when readiness succeeds.

In other words:

- if `ready_waiter` finishes first:
  - readiness succeeded
  - keep `discord_task` running
  - do not cancel it

- if `discord_task` finishes first:
  - Discord startup failed early
  - cancel the temporary `ready_waiter`
  - surface the failure

The safe mental model is:

> `ready_waiter` is disposable.  
> `discord_task` is the actual bot process and must survive the readiness check.

## Root Cause In One Sentence

`wait_for_discord_ready()` treats the successful-ready case as "cancel every task that is still running", but in that case the only still-running task is the real Discord bot task.
