from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.gyms import router as gym_router
from app.api.v1.users import router as user_router
from app.api.v1.announcements import router as announcement_router
from app.api.v1.payments import router as payment_router
from app.api.v1.dieticians import router as dietician_router
from app.api.v1.subscription import router as subscription_router
from app.api.v1.messaging import router as messaging_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.admin_payouts import router as admin_payouts_router
from app.api.ws.chat import websocket_endpoint
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Gym Software API",
    version="1.0",
    docs_url="/",
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Gym Software API",
        version="1.0",
        routes=app.routes,
    )

    if "tags" not in openapi_schema:
        openapi_schema["tags"] = []

    openapi_schema["tags"].append({
        "name": "WebSocket",
        "description": "Real-time messaging via WebSocket (use Postman or WebSocket client to test)"
    })

    openapi_schema["components"]["schemas"]["WebSocketConnection"] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "example": "ws://localhost:8000/ws/chat?token=JWT_TOKEN"
            },
            "description": {
                "type": "string",
                "description": "Connect to WebSocket for real-time messages"
            }
        }
    }

    openapi_schema["paths"]["/ws/chat"] = {
        "get": {
            "tags": ["WebSocket"],
            "summary": "WebSocket Connection for Real-Time Messaging",
            "description": (
                "## Real-Time Messaging WebSocket\n\n"
                "Connect to this WebSocket endpoint to receive real-time messages.\n\n"
                "### Authentication\n"
                "Pass your JWT token as a query parameter: `?token=<your_jwt>`\n\n"
                "### Message Types You Can Send:\n\n"
                "**1. Send a message**\n"
                "```json\n"
                "{\n"
                '    "type": "message",\n'
                '    "payload": {\n'
                '        "receiver_id": "user-uuid",\n'
                '        "content": "Hello!"\n'
                "    }\n"
                "}\n"
                "```\n\n"
                "**2. Keep alive (ping)**\n"
                "```json\n"
                '{"type": "ping"}\n'
                "```\n\n"
                "### Messages You Will Receive:\n\n"
                "**1. New message from someone**\n"
                "```json\n"
                "{\n"
                '    "type": "message",\n'
                '    "payload": {\n'
                '        "message_id": "uuid",\n'
                '        "sender_id": "uuid",\n'
                '        "sender_type": "gym_user",\n'
                '        "receiver_id": "uuid",\n'
                '        "receiver_type": "gym_owner",\n'
                '        "content": "Hello!",\n'
                '        "file_id": null,\n'
                '        "created_at": "2024-01-01T00:00:00"\n'
                "    }\n"
                "}\n"
                "```\n\n"
                "**2. Message sent confirmation**\n"
                "```json\n"
                "{\n"
                '    "type": "sent",\n'
                '    "payload": {\n'
                '        "message_id": "uuid",\n'
                '        "created_at": "2024-01-01T00:00:00"\n'
                "    }\n"
                "}\n"
                "```\n\n"
                "**3. Pong response**\n"
                "```json\n"
                '{"type": "pong"}\n'
                "```\n\n"
                "### Error Responses\n"
                "```json\n"
                '{"type": "error", "message": "Error description"}\n'
                "```"
            ),
            "parameters": [
                {
                    "name": "token",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "JWT access token (obtained from /api/v1/auth/signin)"
                }
            ],
            "responses": {
                "101": {
                    "description": "Switching Protocols - WebSocket connection established"
                },
                "403": {
                    "description": "Forbidden - Invalid or expired token"
                }
            }
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

base = "/api/v1"

app.include_router(health_router, prefix=base + "/health")
app.include_router(dietician_router, prefix=base + "/dieticians")
app.include_router(auth_router, prefix=base + "/auth")
app.include_router(gym_router, prefix=base + "/gyms")
app.include_router(user_router, prefix=base + "/users")
app.include_router(announcement_router, prefix=base + "/announcements")
app.include_router(payment_router, prefix=base + "/payments")
app.include_router(subscription_router, prefix=base + "/subscription-plans")
app.include_router(notifications_router, prefix=base + "/notifications")
app.include_router(messaging_router, prefix=base + "/messages")
app.include_router(admin_payouts_router, prefix=base + "/admin/payouts")
app.add_api_websocket_route("/ws/chat", websocket_endpoint, name="websocket_messages")
