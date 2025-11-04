#!/usr/bin/env python3
"""
PNCP Medical Data Processor - Setup Verification
Verifies all components are properly installed and configured
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version requirement"""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 9):
        print(f"❌ Python 3.9+ required, got {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_dependencies():
    """Check if required dependencies can be imported"""
    print("\n📦 Checking dependencies...")

    required_modules = [
        ('asyncio', 'Built-in async support'),
        ('typing', 'Type hints support'),
        ('dataclasses', 'Data classes support'),
        ('json', 'JSON processing'),
        ('logging', 'Logging support'),
        ('datetime', 'Date/time handling'),
        ('enum', 'Enumerations'),
        ('re', 'Regular expressions'),
    ]

    optional_modules = [
        ('fuzzywuzzy', 'Fuzzy string matching'),
        ('pandas', 'Data analysis'),
        ('aiohttp', 'HTTP client'),
        ('asyncpg', 'PostgreSQL async driver'),
        ('google.cloud.sql.connector', 'Cloud SQL connector'),
        ('sqlalchemy', 'SQL toolkit'),
    ]

    # Check required modules
    success = True
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
        except ImportError:
            print(f"❌ {module} - {description} (REQUIRED)")
            success = False

    # Check optional modules
    print("\n📋 Optional dependencies (install with pip install -r requirements.txt):")
    for module, description in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
        except ImportError:
            print(f"⚠️  {module} - {description} (optional, but recommended)")

    return success

def check_project_structure():
    """Check if all required files are present"""
    print("\n📁 Checking project structure...")

    required_files = [
        'config.py',
        'database.py',
        'pncp_api.py',
        'classifier.py',
        'product_matcher.py',
        'tender_discovery.py',
        'item_processor.py',
        'main.py',
        'requirements.txt',
        'README.md',
        '.env.example'
    ]

    success = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} (MISSING)")
            success = False

    return success

def check_configuration():
    """Check configuration and imports"""
    print("\n⚙️ Checking configuration...")

    try:
        from config import BRAZILIAN_STATES, ProcessingConfig, DatabaseConfig
        print(f"✅ Configuration loaded ({len(BRAZILIAN_STATES)} Brazilian states)")

        config = ProcessingConfig()
        print(f"✅ Default config created ({len(config.enabled_states)} states enabled)")

        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def check_core_modules():
    """Check if core modules can be imported"""
    print("\n🔧 Checking core modules...")

    modules_to_test = [
        ('product_matcher', 'ProductMatcher'),
        ('classifier', 'TenderClassifier'),
    ]

    success = True
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name)
            class_obj = getattr(module, class_name)
            instance = class_obj()
            print(f"✅ {module_name}.{class_name} - Created successfully")
        except Exception as e:
            print(f"❌ {module_name}.{class_name} - Error: {e}")
            success = False

    return success

def check_environment():
    """Check environment configuration"""
    print("\n🌍 Checking environment configuration...")

    env_file_exists = os.path.exists('.env')
    env_example_exists = os.path.exists('.env.example')

    if env_example_exists:
        print("✅ .env.example found - Template available")
    else:
        print("⚠️  .env.example not found")

    if env_file_exists:
        print("✅ .env file found - Environment configured")
    else:
        print("⚠️  .env file not found - Copy from .env.example and configure")

    # Check critical environment variables
    critical_vars = ['PNCP_USERNAME', 'PNCP_PASSWORD', 'GOOGLE_CLOUD_PROJECT']
    configured_vars = 0

    for var in critical_vars:
        if os.getenv(var):
            configured_vars += 1
            print(f"✅ {var} - Configured")
        else:
            print(f"⚠️  {var} - Not configured")

    if configured_vars == len(critical_vars):
        print("✅ All critical environment variables configured")
    else:
        print("⚠️  Some environment variables need configuration")

    return True

def main():
    """Main verification function"""
    print("🔍 PNCP Medical Data Processor - Setup Verification")
    print("=" * 60)

    checks = [
        check_python_version,
        check_dependencies,
        check_project_structure,
        check_configuration,
        check_core_modules,
        check_environment
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print("🎉 ALL CHECKS PASSED - System ready!")
        print("\n🚀 Next steps:")
        print("1. Configure .env file with your credentials")
        print("2. Install optional dependencies: pip install -r requirements.txt")
        print("3. Set up Google Cloud SQL database")
        print("4. Run: python main.py --help")
        return True
    else:
        print(f"⚠️  {passed}/{total} checks passed - Some issues need attention")
        print("\n🔧 To fix issues:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Ensure all Python files are present")
        print("3. Configure environment variables in .env")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)