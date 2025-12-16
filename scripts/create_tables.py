#!/usr/bin/env python3
"""
Simple script to create all tables with print statements.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("🚀 CREATING DATABASE TABLES")
print("=" * 60)

try:
    # Import database engine and Base
    from app.core.database import engine, Base
    print("✅ Database engine imported")
    print(f"📊 Database URL: {engine.url}")
    
    # Import models through __init__.py
    from app.models import (
        User, Session, OTP, OAuthAccount, PasswordResetToken,
        Gym, GymPhoto, GymDocument,
        Dietician, DieticianDocument,
        SubscriptionTier, Subscription, Payment, Payout,
        File,
        Notification, NotificationRecipient,
        Announcement, AnnouncementRead,
        Message,
        Rating,
        Exercise, WorkoutSession, SessionExercise,
        Checkin,
        VerificationApplication, VerificationDocument,
        UserFavoriteGym, ClientAssignment, GymStaff
    )
    
    print("✅ All models imported successfully")
    
    print("\n" + "=" * 60)
    print("🏗️  CREATING TABLES...")
    print("=" * 60)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("\n✅ SUCCESS! All tables created.")
    
    # List all created tables
    table_count = len(Base.metadata.tables)
    print(f"📊 Total tables created: {table_count}")
    print("\n📋 Table List:")
    
    for i, table_name in enumerate(sorted(Base.metadata.tables.keys()), 1):
        print(f"  {i:2d}. {table_name}")
    
    print("\n" + "=" * 60)
    print("🎉 DATABASE READY FOR DEVELOPMENT!")
    print("=" * 60)
    
except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    print(f"\n📁 Current directory: {os.getcwd()}")
    print(f"📁 Looking for models in: {os.path.join(os.getcwd(), 'app', 'models')}")
    
    # List what's in the models directory
    models_dir = os.path.join(os.getcwd(), 'app', 'models')
    if os.path.exists(models_dir):
        print(f"\n📄 Files in models directory:")
        for file in sorted(os.listdir(models_dir)):
            if file.endswith('.py') and file != '__pycache__':
                print(f"  - {file}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()