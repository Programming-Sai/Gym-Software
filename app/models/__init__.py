# app/models/__init__.py

# Core authentication
from .users import User
from .auth import Session, OTP, OAuthAccount, PasswordResetToken

# Gym management
from .gyms import Gym, GymPhoto, GymDocument

# Dietician management
from .dieticians import Dietician, DieticianDocument

# Financial
from .financials import SubscriptionTier, Subscription, Payment, Payout

# File management
from .files import File

# Notifications & Communication
from .notifications import Notification, NotificationRecipient
from .announcements import Announcement, AnnouncementRead
from .messages import Message

# Ratings & Reviews
from .ratings import Rating

# Fitness & Workouts
from .goals import Exercise, WorkoutSession, SessionExercise
from .checkins import Checkin

# Verification system
from .verifications import VerificationApplication, VerificationDocument

# Relationships
from .relationships import UserFavoriteGym, ClientAssignment, GymStaff

# Optional: export all
__all__ = [
    # Authentication
    "User",
    "Session", "OTP", "OAuthAccount", "PasswordResetToken",
    
    # Gym
    "Gym", "GymPhoto", "GymDocument",
    
    # Dietician
    "Dietician", "DieticianDocument",
    
    # Financial
    "SubscriptionTier", "Subscription", "Payment", "Payout",
    
    # Files
    "File",
    
    # Communication
    "Notification", "NotificationRecipient",
    "Announcement", "AnnouncementRead",
    "Message",
    
    # Ratings
    "Rating",
    
    # Fitness
    "Exercise", "WorkoutSession", "SessionExercise",
    "Checkin",
    
    # Verification
    "VerificationApplication", "VerificationDocument",
    
    # Relationships
    "UserFavoriteGym", "ClientAssignment", "GymStaff",
]