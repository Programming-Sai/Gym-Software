import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import func
from app.core.config import settings
from app.models.notifications import DeviceToken, Notification, NotificationRecipient
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class FCMService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            if firebase_admin._apps:
                logger.info("Firebase already initialized")
                self.enabled = True
                return
            
            cred_dict = settings.firebase_credentials_dict
            
            if not cred_dict:
                logger.warning("Firebase credentials not found. Push notifications disabled.")
                self.enabled = False
                return
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")
            self.enabled = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.enabled = False

    def _send_fcm(self, tokens: List[str], title: str, body: str, data: dict = None, image_url: str = None) -> dict:
        """Internal method to send FCM push"""
        if not self.enabled or not tokens:
            return {"success": 0, "failed": len(tokens) if tokens else 0}

        try:
            valid_tokens = [t for t in tokens if t]
            if not valid_tokens:
                return {"success": 0, "failed": len(tokens)}

            notification = messaging.Notification(
                title=title[:100],
                body=body[:1024],
            )
            if image_url:
                notification.image = image_url

            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=valid_tokens,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(sound="default")
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default")
                    )
                ),
            )

            response = messaging.send_multicast(message)
            return {
                "success": response.success_count,
                "failed": response.failure_count
            }

        except Exception as e:
            logger.error(f"Failed to send multicast: {e}")
            return {"success": 0, "failed": len(tokens)}

    def send(
        self,
        db: Session,
        user_ids: List[str],
        title: str,
        body: str,
        notification_type: str = "info",
        scope: str = "individual",
        data: dict = None,
        image_url: str = None,
        send_push: bool = True
    ) -> List[str]:
        """
        Send notification to multiple users.
        
        Args:
            db: Database session
            user_ids: List of recipient user IDs
            title: Notification title
            body: Notification body
            notification_type: info, alert, reminder, achievement
            scope: individual, group, all
            data: Additional per-user data
            image_url: Optional image URL
            send_push: Whether to send FCM push
        
        Returns:
            List of notification IDs created
        """
        if not user_ids:
            return []
        
        notification_ids = []
        
        # Create Notification record
        notification = Notification(
            type=notification_type,
            scope=scope,
            title=title,
            message=body,
            image_url=image_url,
            sent_at=func.now()
        )
        db.add(notification)
        db.flush()
        
        # Create recipient records and collect push tokens
        all_tokens = []
        
        for user_id in user_ids:
            recipient = NotificationRecipient(
                notification_id=notification.notification_id,
                user_id=user_id,
                data=data or {}
            )
            db.add(recipient)
            
            # Collect device tokens for push
            if send_push:
                tokens = db.query(DeviceToken.fcm_token).filter(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True
                ).all()
                all_tokens.extend([t[0] for t in tokens])
        
        db.commit()
        notification_ids.append(notification.notification_id)
        
        # Send push if enabled
        if send_push and all_tokens:
            self._send_fcm(
                tokens=all_tokens,
                title=title,
                body=body,
                data={
                    "type": "notification",
                    "notification_id": notification.notification_id,
                    **(data or {})
                },
                image_url=image_url
            )
        
        return notification_ids

    def send_to_user(
        self,
        db: Session,
        user_id: str,
        title: str,
        body: str,
        notification_type: str = "info",
        data: dict = None,
        image_url: str = None,
        send_push: bool = True
    ) -> Optional[str]:
        """Send notification to a single user"""
        notification_ids = self.send(
            db=db,
            user_ids=[user_id],
            title=title,
            body=body,
            notification_type=notification_type,
            scope="individual",
            data=data,
            image_url=image_url,
            send_push=send_push
        )
        return notification_ids[0] if notification_ids else None

    def mark_as_read(self, db: Session, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        recipient = db.query(NotificationRecipient).filter(
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.notification_id == notification_id
        ).first()
        
        if recipient:
            recipient.is_read = True
            db.commit()
            return True
        return False

    def get_unread_count(self, db: Session, user_id: str) -> int:
        """Get unread notification count"""
        return db.query(NotificationRecipient).filter(
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.is_read == False
        ).count()

    def get_notifications(
        self,
        db: Session,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Get paginated notifications for a user"""
        recipients = db.query(NotificationRecipient).filter(
            NotificationRecipient.user_id == user_id
        ).order_by(
            NotificationRecipient.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        result = []
        for r in recipients:
            result.append({
                "notification_id": r.notification_id,
                "type": r.notification.type,
                "title": r.notification.title,
                "message": r.notification.message,
                "image_url": r.notification.image_url,
                "is_read": r.is_read,
                "data": r.data,
                "created_at": r.created_at,
                "delivered_at": r.delivered_at
            })
        
        return result


# Singleton instance
fcm_service = FCMService()