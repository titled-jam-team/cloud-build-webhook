import base64
import json
import aiohttp
import os
import iso8601
import fastapi
import pydantic
import hypercorn.asyncio
import asyncio

app = fastapi.FastAPI()
http: aiohttp.ClientSession


status_to_emoji_map = {
    "STATUS_UNKNOWN": "<:help:997606686200185033>",
    "PENDING": "<:downloading:997606683121553458>",
    "QUEUED": "<:hourglass_bottom:997606687844356186>",
    "WORKING": "<:construction:997606681716457493>",
    "SUCCESS": "<:check_circle:997606680374292530>",
    "FAILURE": "<:error:997606685092872362>",
    "INTERNAL_ERROR": "<:error:997606685092872362>",
    "TIMEOUT": "<:timer_off:997606689421414421>",
    "CANCELLED": "<:cancel:997609185497845862>",
    "EXPIRED": "<:timer_off:997606689421414421>"
}


status_to_name_map = {
    "STATUS_UNKNOWN": "unknown",
    "PENDING": "pending",
    "QUEUED": "queued",
    "WORKING": "running",
    "SUCCESS": "succeeded",
    "FAILURE": "failed",
    "INTERNAL_ERROR": "errored",
    "TIMEOUT": "timed out",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired"
}


class PubsubMessage(pydantic.BaseModel, extra=pydantic.Extra.allow):
    data: str


class PubsubPayload(pydantic.BaseModel, extra=pydantic.Extra.allow):
    message: PubsubMessage


@app.post("/")
async def on_build(payload: PubsubPayload):
    build = json.loads(base64.b64decode(payload.message.data))

    start_time = iso8601.parse_date(build.get('startTime'))
    create_time = iso8601.parse_date(build.get('createTime'))
    finish_time = iso8601.parse_date(build.get('finishTime'))
    status = build.get('status')
    approval = build.get('approval')
    extra_info = []

    if status == "PENDING" or status == "QUEUED":
        if approval.get('state') == "PENDING":
            status_string = "awaiting approval"
            status_emoji = "<:account_circle:997606678809817128>"
        elif approval.get('state') == "APPROVED":
            status_string = f"approved by {approval.get('result').get('approverAccount')} in {(finish_time - start_time).seconds}s."
            status_emoji = status_to_emoji_map.get(status)
    elif status == "CANCELLED" and approval.get('state') == "REJECTED":
        status_string = f"rejected by {approval.get('result').get('approverAccount')} in {(finish_time - start_time).seconds}s."
        status_emoji = "<:cancel:997609185497845862>"
    else:
        status_string = f"{status_to_name_map.get(status)} in {(finish_time - start_time).seconds}s."
        status_emoji = status_to_emoji_map.get(status)

    if status == "PENDING" or status == "QUEUED":
        time_string = f"Created: <t:{int(create_time.timestamp())}:R>"
    elif status == "WORKING":
        time_string = f"Created: <t:{int(create_time.timestamp())}:R>\nStarted: <t:{int(start_time.timestamp())}:R>"
    else:
        time_string = f"Created: <t:{int(create_time.timestamp())}:R>\nStarted: <t:{int(start_time.timestamp())}:R>\nFinished: <t:{int(start_time.timestamp())}:R>"

    if status == "SUCCESS":
        for artifact in build.get("artifacts").get("images"):
            extra_info.append(f"Docker artifact: `{artifact}`")

        if preview := build.get("substitutions").get("_PREVIEW_URL"):
            extra_info.append(f"Preview: {preview.format(**build.get('substitutions'))}")

    extra_info_formatted = '\n'.join(extra_info)

    embed = {
        "embeds": [
            {
                "title": f"Build {build.get('id')}",
                "description": (
                    f"{status_emoji} Build {status_string}\n\n"
                    f"{extra_info_formatted}\n\n"
                    f"{time_string}\n"
                ),
                "footer": {
                    "text": "Cloud Build"
                },
                "timestamp": create_time.isoformat()
            }
        ]
    }

    print(json.dumps(embed))

    async with http.post(os.environ.get("DISCORD_WEBHOOK_URL"), json=embed) as req:
        print(await req.read())


@app.on_event("startup")
async def get_http():
    global http

    http = aiohttp.ClientSession()


if __name__ == "__main__":
    config = hypercorn.config.Config()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', 8080)}"]
    config.accesslog = "-"

    if os.environ.get("DEV") == "1":
        config.use_reloader = True

    if os.name == 'posix':
        import uvloop
        uvloop.install()

    asyncio.run(hypercorn.asyncio.serve(app, config))  # noqa