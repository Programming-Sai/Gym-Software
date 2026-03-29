from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_session, get_current_user
from app.models.users import User
from app.models.notifications import DeviceToken, NotificationRecipient
from app.models.auth import Session as AuthSession
from app.schemas.notifications import DeviceRegistrationRequest, DeviceRegistrationResponse
from app.services.fcm_service import fcm_service


router = APIRouter(tags=["Notifications"])
logger = logging.getLogger(__name__)




@router.post("/register", response_model=DeviceRegistrationResponse)
def register_device(
    request: DeviceRegistrationRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_session: User = Depends(get_current_session)
):
    if not request.fcm_token:
        raise HTTPException(status_code=400, detail="fcm_token is required")
    
    # 1. Check if this exact FCM token already exists
    existing_token = db.query(DeviceToken).filter(
        DeviceToken.fcm_token == request.fcm_token
    ).first()
    
    if existing_token:
        # Same device, update it
        existing_token.user_id = current_user.user_id
        existing_token.device_info = request.device_info
        existing_token.is_active = True
        db.commit()
        return DeviceRegistrationResponse(
            status="success",
            message="Device token updated",
            token_id=existing_token.token_id
        )
    
    # 2. Check if this session already has a token (same device, new FCM token)
    session_token = db.query(DeviceToken).filter(
        DeviceToken.session_id == current_session.session_id,
        DeviceToken.user_id == current_user.user_id
    ).first()
    
    if session_token:
        # Update existing token for this session
        session_token.fcm_token = request.fcm_token
        session_token.device_info = request.device_info
        session_token.is_active = True
        db.commit()
        return DeviceRegistrationResponse(
            status="success",
            message="Session token updated",
            token_id=session_token.token_id
        )
    
    # 3. Create new token
    device_token = DeviceToken(
        user_id=current_user.user_id,
        session_id=current_session.session_id,
        fcm_token=request.fcm_token,
        device_info=request.device_info,
        is_active=True
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)
    
    return DeviceRegistrationResponse(
        status="success",
        message="Device registered for push notifications",
        token_id=device_token.token_id
    )

@router.delete("/unregister", response_model=DeviceRegistrationResponse)
def unregister_device(
    fcm_token: str,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove specific device token for current user.
    """
    device_token = db.query(DeviceToken).filter(
        DeviceToken.fcm_token == fcm_token,
        DeviceToken.user_id == current_user.user_id
    ).first()

    if device_token:
        db.delete(device_token)
        db.commit()
        logger.info(f"Unregistered device token {fcm_token} for user {current_user.user_id}")
        return DeviceRegistrationResponse(
            status="success",
            message="Device unregistered",
            token_id=device_token.token_id
        )

    return DeviceRegistrationResponse(
        status="success",
        message="Token not found or already unregistered",
        token_id=None
    )


@router.delete("/unregister-all")
def unregister_all_devices(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove all device tokens for current user (on logout from all devices).
    """
    count = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.user_id
    ).delete()
    db.commit()

    return {
        "status": "success",
        "message": f"Unregistered {count} device(s)",
        "count": count
    }


@router.get("/tokens")
def get_device_tokens(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all active device tokens for current user.
    """
    tokens = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.user_id,
        DeviceToken.is_active == True
    ).all()

    return {
        "status": "success",
        "tokens": [
            {
                "token_id": t.token_id,
                "device_info": t.device_info,
                "last_used_at": t.last_used_at,
                "created_at": t.created_at
            }
            for t in tokens
        ],
        "count": len(tokens)
    }


@router.get("/inbox")
def get_notifications(
    limit: int = 50,
    offset: int = 0,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's notification inbox"""
    notifications = fcm_service.get_notifications(db, current_user.user_id, limit, offset)
    unread_count = fcm_service.get_unread_count(db, current_user.user_id)
    
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset
    }


@router.post("/inbox/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    if fcm_service.mark_as_read(db, current_user.user_id, notification_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/inbox/read-all")
def mark_all_read(  
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""

    unread_count = db.query(NotificationRecipient).filter(
        NotificationRecipient.user_id == current_user.user_id,
        NotificationRecipient.is_read == False
    ).count()


    db.query(NotificationRecipient).filter(
        NotificationRecipient.user_id == current_user.user_id,
        NotificationRecipient.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {
        "status": "success",
        "message": f"Marked {unread_count} notifications as read",
        "count": unread_count
    }


@router.post("/test-notification")
def test_notification(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a test notification for the current user"""
    
    notification_id = fcm_service.send_to_user(
        db=db,
        user_id=current_user.user_id,
        title="Test Notification",
        body="This is a test notification from the API",
        notification_type="info",
        data={"test": True},
        send_push=False  # Don't send push for test
    )
    
    return {
        "status": "success",
        "notification_id": notification_id,
        "message": "Test notification created"
    }





