#!/usr/bin/env python3
"""
Complete Database Setup for PNCP Medical Processing
Run this after the Cloud SQL instance is ready
"""

import os
import asyncio
import subprocess
import time
from datetime import datetime

async def wait_for_instance():
    """Wait for Cloud SQL instance to be ready"""
    print("⏳ Waiting for Cloud SQL instance to be ready...")

    while True:
        try:
            result = subprocess.run([
                'gcloud', 'sql', 'instances', 'describe', 'pncp-medical-db',
                '--format=value(state)'
            ], capture_output=True, text=True, check=True)

            status = result.stdout.strip()
            if status == 'RUNNABLE':
                print("✅ Instance is ready!")
                return True
            else:
                print(f"⏳ Instance status: {status} - waiting...")
                await asyncio.sleep(30)

        except subprocess.CalledProcessError as e:
            print(f"❌ Error checking instance: {e}")
            return False

def create_database():
    """Create the database"""
    print("🗄️ Creating database 'pncp_medical_data'...")
    try:
        result = subprocess.run([
            'gcloud', 'sql', 'databases', 'create', 'pncp_medical_data',
            '--instance=pncp-medical-db'
        ], capture_output=True, text=True, check=True)
        print("✅ Database created successfully")
        return True
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            print("✅ Database already exists")
            return True
        else:
            print(f"❌ Error creating database: {e}")
            return False

def setup_iam_auth():
    """Set up IAM authentication"""
    print("🔐 Setting up IAM database authentication...")

    try:
        # Get current user email
        result = subprocess.run([
            'gcloud', 'config', 'get-value', 'account'
        ], capture_output=True, text=True, check=True)

        user_email = result.stdout.strip()
        print(f"👤 Current user: {user_email}")

        # Add IAM database user
        try:
            subprocess.run([
                'gcloud', 'sql', 'users', 'create', user_email,
                '--instance=pncp-medical-db',
                '--type=cloud_iam_user'
            ], check=True)
            print(f"✅ IAM database user created: {user_email}")
        except subprocess.CalledProcessError:
            print(f"⚠️  IAM user {user_email} may already exist")

        # Grant Cloud SQL Client role
        subprocess.run([
            'gcloud', 'projects', 'add-iam-policy-binding', 'medical-473219',
            f'--member=user:{user_email}',
            '--role=roles/cloudsql.client'
        ], check=True)

        print("✅ IAM authentication configured")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up IAM auth: {e}")
        return False

async def initialize_schema():
    """Initialize database schema"""
    print("📊 Initializing database schema...")

    try:
        # Import database modules
        from database import create_db_manager_from_env, DatabaseOperations

        # Create database manager
        db_manager = create_db_manager_from_env()
        db_ops = DatabaseOperations(db_manager)

        # Initialize schema
        await db_ops.initialize_database()
        await db_manager.close()

        print("✅ Database schema initialized")
        return True

    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        return False

def display_connection_info():
    """Display connection information"""
    print("\n📊 Database Connection Information:")
    print("=" * 50)
    print(f"Project ID: medical-473219")
    print(f"Instance Name: pncp-medical-db")
    print(f"Region: us-central1")
    print(f"Database: pncp_medical_data")
    print(f"Connection Name: medical-473219:us-central1:pncp-medical-db")

    try:
        # Get instance IP
        result = subprocess.run([
            'gcloud', 'sql', 'instances', 'describe', 'pncp-medical-db',
            '--format=value(ipAddresses[0].ipAddress)'
        ], capture_output=True, text=True, check=True)

        instance_ip = result.stdout.strip()
        print(f"Public IP: {instance_ip}")

    except subprocess.CalledProcessError:
        print("Public IP: (could not retrieve)")

    print("\n✅ Your .env file is already configured with these settings!")

async def test_connection():
    """Test database connection"""
    print("\n🧪 Testing database connection...")

    try:
        from database import create_db_manager_from_env

        db_manager = create_db_manager_from_env()

        # Test connection
        conn = await db_manager.get_connection()

        # Run simple query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Database connection successful!")
        print(f"📋 PostgreSQL version: {result}")

        await conn.close()
        await db_manager.close()

        return True

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

async def main():
    """Main setup function"""
    print("🔧 PNCP Medical Data Processor - Database Setup")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: Wait for instance
    if not await wait_for_instance():
        print("❌ Setup failed - instance not ready")
        return

    # Step 2: Create database
    if not create_database():
        print("❌ Setup failed - could not create database")
        return

    # Step 3: Set up IAM authentication
    if not setup_iam_auth():
        print("❌ Setup failed - could not set up IAM auth")
        return

    # Step 4: Initialize schema
    print("\n⏳ Installing dependencies for schema initialization...")
    try:
        subprocess.run(['pip', 'install', 'asyncpg', 'google-cloud-sql-connector'], check=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("⚠️  Could not install dependencies - you may need to do this manually")

    if not await initialize_schema():
        print("⚠️  Schema initialization failed - you can try this manually later")

    # Step 5: Display connection info
    display_connection_info()

    # Step 6: Test connection
    await test_connection()

    print("\n" + "=" * 60)
    print("🎉 Database setup complete!")
    print("\n🚀 Next steps:")
    print("1. Add your PNCP credentials to .env file")
    print("2. Run: python verify_setup.py")
    print("3. Start processing: python main.py --help")

if __name__ == "__main__":
    asyncio.run(main())