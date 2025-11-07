# Project Reorganization Guide for Claude
**A Step-by-Step Guide for Reorganizing Python Project Root Directories**

---

## 📋 Overview

This guide provides instructions for Claude (or any developer) to reorganize a Python project's root directory following best practices. This pattern was successfully applied to the PNCP Medical Data Processor project and can be adapted to similar Python projects.

---

## 🎯 Goals

1. **Clean Root Directory** - Only essential files (main entry points, README, config)
2. **Organized Code** - Core modules grouped in a `/src` package
3. **Centralized Configuration** - Config files in `/config` directory
4. **SQL Organization** - Database scripts in `/sql` directory
5. **Maintainable Imports** - Clear, consistent import patterns
6. **Zero Breakage** - All existing functionality continues to work

---

## 📖 Step-by-Step Instructions for Claude

### STEP 1: Analyze Current Structure

**Instructions:**
1. Read the README.md to understand the project
2. Identify the main entry point (usually `main.py` or `app.py`)
3. List all Python modules in the root directory
4. Identify configuration files (`.json`, `.yaml`, `.env`, credentials)
5. Find SQL files and database scripts
6. Map out import dependencies between modules

**Commands to run:**
```bash
# List Python files in root
ls -la *.py 2>/dev/null

# List config files
ls -la *.json *.yaml *.yml *.env* 2>/dev/null

# List SQL files
ls -la *.sql 2>/dev/null

# Check existing subdirectories
ls -d */ 2>/dev/null

# Find import patterns
grep -r "^from \|^import " *.py 2>/dev/null | head -20
```

**What to look for:**
- ✅ Core application modules (business logic)
- ✅ Configuration files
- ✅ Database/SQL files
- ✅ Entry point scripts (main.py, app.py, run.py)
- ✅ Utility scripts vs core modules
- ✅ Test files
- ✅ Documentation files

---

### STEP 2: Plan the New Structure

**Create this directory structure:**

```
/ProjectRoot
├── main.py                    # Main entry point (keep in root)
├── app.py                     # Alternative entry point (keep in root)
├── README.md                  # Documentation (keep in root)
├── requirements.txt           # Dependencies (keep in root)
├── .env                       # Environment config (keep in root)
├── .env.example              # Environment template (keep in root)
├── .gitignore                # Git config (keep in root)
│
├── /src                      # NEW - Core application modules
│   ├── __init__.py           # Package initializer
│   ├── config.py             # Configuration module
│   ├── database.py           # Database module
│   ├── api.py                # API client module
│   ├── models.py             # Data models
│   ├── utils.py              # Utilities
│   └── [other_modules].py   # Other core modules
│
├── /config                   # NEW - Configuration files
│   ├── settings.json         # App settings
│   ├── credentials.json      # Credentials (ensure in .gitignore)
│   ├── keywords.json         # Data files
│   └── [other_configs].*    # Other config files
│
├── /sql                      # NEW - SQL scripts
│   ├── schema.sql           # Database schema
│   ├── migrations/          # Migration scripts
│   └── views.sql            # View definitions
│
├── /scripts                  # Utility scripts (keep)
├── /tests                    # Test files (keep)
├── /docs                     # Documentation (keep)
├── /data                     # Data files (keep)
└── /logs                     # Log files (keep)
```

**Decision Rules:**

**Move to `/src`:**
- ✅ Core business logic modules
- ✅ Database connection/ORM modules
- ✅ API clients
- ✅ Model/schema definitions
- ✅ Service/processor classes
- ✅ Utility modules used across the project

**Keep in Root:**
- ✅ Main entry points (main.py, app.py, run.py)
- ✅ README, LICENSE, .gitignore
- ✅ requirements.txt, setup.py, pyproject.toml
- ✅ .env files (but add .env to .gitignore)
- ✅ Convenience shell scripts (run.sh, deploy.sh)

**Move to `/config`:**
- ✅ JSON/YAML configuration files
- ✅ Credential files (ensure they're gitignored)
- ✅ API keys, tokens
- ✅ Static data files used for configuration

**Move to `/sql`:**
- ✅ Schema definition files
- ✅ Migration scripts
- ✅ View/function definitions
- ✅ Python scripts that generate/manage SQL

**Don't Move:**
- ❌ Existing organized directories (tests/, docs/, data/, scripts/)
- ❌ Virtual environment folders (venv/, .venv/)
- ❌ IDE folders (.vscode/, .idea/)
- ❌ Git folder (.git/)

---

### STEP 3: Create New Directories

**Commands:**
```bash
# Create new directories
mkdir -p src config sql

# Create __init__.py for src package
touch src/__init__.py
```

**Add to `src/__init__.py`:**
```python
"""
[Project Name] - Core Modules

This package contains the core application modules.
"""

__version__ = "1.0.0"
```

---

### STEP 4: Move Files (Using Git)

**Important:** Use `git mv` for files tracked by git, regular `mv` for untracked files.

**Commands:**
```bash
# Test which files are tracked
git ls-files *.py

# Move tracked Python modules to src/
git mv module1.py module2.py module3.py src/

# Move untracked config files
mv config.json credentials.json keywords.json config/

# Move SQL files
git mv schema.sql views.sql sql/
mv other_sql_script.py sql/

# Move random data files to appropriate folder
mv random_data.csv data/
```

**Example for PNCP Medical Project pattern:**
```bash
# Core modules → src/
git mv classifier.py config.py database.py pncp_api.py src/
git mv product_matcher.py optimized_discovery.py src/
git mv fetch_and_save_items.py match_tender_items.py src/
git mv org_cache.py src/

# Config files → config/
mv keywords.json fernandes_products.json pncp-key.json config/

# SQL files → sql/
git mv looker_views.sql sql/
mv create_value_filtered_views.py sql/
```

---

### STEP 5: Update Imports in Main Entry Point

**Pattern:**
```python
# BEFORE
from config import Settings
from database import Database
from api import APIClient

# AFTER
from src.config import Settings
from src.database import Database
from src.api import APIClient
```

**Commands to update `main.py` (or primary entry point):**
```bash
# Use sed to update imports (macOS)
sed -i '' 's/^from config import/from src.config import/g' main.py
sed -i '' 's/^from database import/from src.database import/g' main.py
sed -i '' 's/^from api import/from src.api import/g' main.py

# For Linux, use:
# sed -i 's/^from config import/from src.config import/g' main.py
```

**Or manually edit each import:**
- Open main.py
- Find: `from module_name import`
- Replace: `from src.module_name import`

---

### STEP 6: Update Imports Within src/ Modules

**Pattern - Use Relative Imports:**
```python
# BEFORE (when modules were in root)
from config import Settings
from database import Database
from utils import helper_function

# AFTER (modules in same package)
from .config import Settings
from .database import Database
from .utils import helper_function
```

**Automated update for all src/ files:**
```bash
# Find and replace in all Python files in src/
cd src
sed -i '' 's/^from config import/from .config import/g' *.py
sed -i '' 's/^from database import/from .database import/g' *.py
sed -i '' 's/^from api import/from .api import/g' *.py
sed -i '' 's/^from models import/from .models import/g' *.py
sed -i '' 's/^from utils import/from .utils import/g' *.py
# Add more as needed for your specific modules
```

**Important Notes:**
- Use `.module` for modules in the **same directory** (relative imports)
- Use `from src.module` for imports from **outside src/** (absolute imports)
- Relative imports only work when src/ is a package (has `__init__.py`)

---

### STEP 7: Update Imports in Scripts, Tests, and Other Directories

**Pattern:**
```python
# In files OUTSIDE src/ (tests/, scripts/, etc.)
# BEFORE
from config import Settings
from database import Database

# AFTER
from src.config import Settings
from src.database import Database
```

**Automated update:**
```bash
# Update all files in scripts/
find scripts -name "*.py" -type f -exec sed -i '' 's/^from config import/from src.config import/g' {} \;
find scripts -name "*.py" -type f -exec sed -i '' 's/^from database import/from src.database import/g' {} \;

# Update all files in tests/
find tests -name "*.py" -type f -exec sed -i '' 's/^from config import/from src.config import/g' {} \;
find tests -name "*.py" -type f -exec sed -i '' 's/^from database import/from src.database import/g' {} \;

# Update any other directories
find ai_matching -name "*.py" -type f -exec sed -i '' 's/^from config import/from src.config import/g' {} \;
```

**For Linux, remove the `''` after `-i`:**
```bash
find scripts -name "*.py" -exec sed -i 's/^from config import/from src.config import/g' {} \;
```

---

### STEP 8: Update File Paths for Config Files

**Find all references to config files:**
```bash
# Search for hardcoded config file paths
grep -r "config\.json\|settings\.json\|credentials\.json" . --include="*.py"
grep -r "keywords\.json\|\.json" . --include="*.py" | grep open
```

**Pattern:**
```python
# BEFORE
with open('config.json', 'r') as f:
with open('keywords.json', 'r') as f:
with open('credentials.json', 'r') as f:

# AFTER
with open('config/config.json', 'r') as f:
with open('config/keywords.json', 'r') as f:
with open('config/credentials.json', 'r') as f:
```

**Update file paths:**
```bash
# Use sed to update config file paths
sed -i '' "s|'config\.json'|'config/config.json'|g" src/*.py
sed -i '' "s|'keywords\.json'|'config/keywords.json'|g" src/*.py
sed -i '' "s|'credentials\.json'|'config/credentials.json'|g" src/*.py
```

**Or use a more generic approach:**
```python
# Better: Use pathlib for cross-platform compatibility
from pathlib import Path

# In your config module
CONFIG_DIR = Path(__file__).parent.parent / 'config'
KEYWORDS_FILE = CONFIG_DIR / 'keywords.json'
CREDENTIALS_FILE = CONFIG_DIR / 'credentials.json'

# Usage
with open(KEYWORDS_FILE, 'r') as f:
    keywords = json.load(f)
```

---

### STEP 9: Update SQL File Paths

**Pattern:**
```python
# BEFORE
with open('schema.sql', 'r') as f:
with open('views.sql', 'r') as f:

# AFTER
with open('sql/schema.sql', 'r') as f:
with open('sql/views.sql', 'r') as f:
```

**Find and update:**
```bash
# Search for SQL file references
grep -r "\.sql" . --include="*.py" | grep -v ".git"

# Update paths
sed -i '' "s|'schema\.sql'|'sql/schema.sql'|g" src/*.py setup/*.py
sed -i '' "s|'views\.sql'|'sql/views.sql'|g" src/*.py
```

---

### STEP 10: Verify All Imports Work

**Test import hierarchy:**
```bash
# Test that core modules can be imported
python3 -c "from src.config import *; print('✅ src.config imports work')"
python3 -c "from src.database import *; print('✅ src.database imports work')"
python3 -c "from src.api import *; print('✅ src.api imports work')"

# Test main entry point
python3 main.py --help

# Or if your project has a different test command
python3 app.py --version
```

**Run existing tests:**
```bash
# If you have pytest
pytest tests/

# If you have unittest
python3 -m unittest discover tests/

# Run a quick sanity check script
python3 tests/test_imports.py
```

**Manual verification checklist:**
- [ ] Main entry point runs without import errors
- [ ] Help/version command works
- [ ] All modules in src/ import correctly
- [ ] All scripts in scripts/ run without import errors
- [ ] All tests pass
- [ ] Config files are found at new paths
- [ ] SQL files are found at new paths

---

### STEP 11: Update .gitignore

**Add new patterns:**
```bash
# Add to .gitignore
echo "" >> .gitignore
echo "# Configuration - sensitive files" >> .gitignore
echo "config/credentials.json" >> .gitignore
echo "config/pncp-key.json" >> .gitignore
echo "config/*.key" >> .gitignore
echo "config/secrets.*" >> .gitignore
echo "" >> .gitignore
echo "# Python cache in src" >> .gitignore
echo "src/__pycache__/" >> .gitignore
echo "src/**/__pycache__/" >> .gitignore
```

**Verify gitignore:**
```bash
# Check what would be committed
git status

# Make sure sensitive files are not tracked
git ls-files | grep -i "credential\|secret\|key\|password"
```

---

### STEP 12: Clean Up Root Directory

**Remove empty files or unnecessary duplicates:**
```bash
# List what's left in root
ls -lah *.py *.json *.sql 2>/dev/null

# Check if any files were missed
echo "=== Files remaining in root ==="
ls -1 *.py 2>/dev/null || echo "No Python files in root (expected: only entry points)"
ls -1 *.json 2>/dev/null || echo "No JSON files in root (good!)"
ls -1 *.sql 2>/dev/null || echo "No SQL files in root (good!)"
```

**Expected root directory after cleanup:**
```
/ProjectRoot
├── main.py (or app.py)        # Entry point only
├── run.sh                      # Shell script (if any)
├── README.md
├── LICENSE
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── src/                        # All modules here
├── config/                     # All config here
├── sql/                        # All SQL here
└── [existing organized dirs]   # Keep as-is
```

---

### STEP 13: Update Documentation

**Update README.md:**
```markdown
## 📁 Project Structure

\`\`\`
/ProjectName
├── main.py                    # Main entry point
├── /src                       # Core application modules
│   ├── config.py             # Configuration
│   ├── database.py           # Database operations
│   └── ...                   # Other modules
├── /config                    # Configuration files
├── /sql                       # Database scripts
├── /scripts                   # Utility scripts
├── /tests                     # Test files
└── /data                      # Data files
\`\`\`

## 🚀 Quick Start

\`\`\`bash
# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your settings

# Run the application
python3 main.py
\`\`\`
```

**Create a migration guide (optional):**
Create `REORGANIZATION_SUMMARY.md` documenting:
- What changed
- Why it changed
- How to update custom scripts
- Verification steps

---

### STEP 14: Commit Changes

**Git commit strategy:**
```bash
# Stage the reorganization
git add src/ config/ sql/
git add main.py  # Updated imports
git add .gitignore  # Updated patterns
git add README.md  # Updated docs (if modified)

# Commit the reorganization
git commit -m "Reorganize project structure

- Move core modules to src/ package
- Move config files to config/ directory
- Move SQL files to sql/ directory
- Update all imports to use new structure
- Update .gitignore for new directories
- Clean up root directory

All functionality verified working."

# If you want separate commits:
git add src/
git commit -m "Move core modules to src/ package"

git add config/
git commit -m "Move config files to config/ directory"

git add sql/
git commit -m "Move SQL files to sql/ directory"

git add main.py scripts/ tests/
git commit -m "Update imports for new structure"
```

---

## 🔧 Common Patterns & Solutions

### Pattern 1: Module Imports Another Module in src/

**Before (both in root):**
```python
# In database.py
from config import DATABASE_URL

# In api.py
from database import Database
```

**After (both in src/):**
```python
# In src/database.py
from .config import DATABASE_URL

# In src/api.py
from .database import Database
```

### Pattern 2: Main Entry Point Imports from src/

**In main.py (root):**
```python
from src.config import Settings
from src.database import Database
from src.api import APIClient

def main():
    config = Settings()
    db = Database(config)
    api = APIClient(config)
    # ... rest of code
```

### Pattern 3: Scripts Import from src/

**In scripts/utility.py:**
```python
from src.config import Settings
from src.database import Database

def run_utility():
    db = Database()
    # ... utility code
```

### Pattern 4: Tests Import from src/

**In tests/test_database.py:**
```python
import pytest
from src.database import Database
from src.config import Settings

def test_database_connection():
    db = Database(Settings())
    assert db.connect()
```

### Pattern 5: Reading Config Files with Path

**Bad (hardcoded path):**
```python
with open('config.json', 'r') as f:
    config = json.load(f)
```

**Good (relative to project root):**
```python
from pathlib import Path

# Get project root (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / 'config' / 'config.json'

with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)
```

**Better (centralized in config module):**
```python
# In src/config.py
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / 'config'

def load_config(filename):
    with open(CONFIG_DIR / filename, 'r') as f:
        return json.load(f)

# In other modules
from .config import load_config
settings = load_config('settings.json')
```

---

## 🚨 Common Issues & Solutions

### Issue 1: ImportError: attempted relative import with no known parent package

**Error:**
```
ImportError: attempted relative import with no known parent package
```

**Cause:** Running a module directly that uses relative imports

**Solution:** Run as module or from project root
```bash
# Bad (if module uses relative imports)
python3 src/database.py

# Good
python3 -m src.database

# Or use main entry point
python3 main.py
```

### Issue 2: ModuleNotFoundError: No module named 'src'

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Cause:** Running script from wrong directory

**Solution:** Always run from project root
```bash
# Bad
cd scripts
python3 utility.py

# Good
cd /path/to/project_root
python3 scripts/utility.py
```

### Issue 3: FileNotFoundError: config/settings.json

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/settings.json'
```

**Cause:** Relative path assumed from different working directory

**Solution:** Use absolute paths from project root
```python
from pathlib import Path

# Get project root
if __file__:
    PROJECT_ROOT = Path(__file__).parent.parent
else:
    PROJECT_ROOT = Path.cwd()

CONFIG_FILE = PROJECT_ROOT / 'config' / 'settings.json'
```

### Issue 4: Circular imports

**Error:**
```
ImportError: cannot import name 'X' from partially initialized module 'src.Y'
```

**Cause:** Two modules importing each other

**Solution 1:** Refactor to remove circular dependency
```python
# Extract shared code to a third module
# src/shared.py - common code
# src/module_a.py - imports from shared
# src/module_b.py - imports from shared
```

**Solution 2:** Use lazy imports
```python
# Instead of top-level import
def function_that_needs_module():
    from .other_module import SomeClass
    return SomeClass()
```

### Issue 5: Tests can't find modules

**Error in tests:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution 1:** Add project root to Python path in conftest.py
```python
# tests/conftest.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

**Solution 2:** Install package in development mode
```bash
# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="your-project",
    version="0.1.0",
    packages=find_packages(),
)
EOF

# Install in editable mode
pip install -e .
```

---

## ✅ Verification Checklist

Before considering the reorganization complete, verify:

### Import Verification
- [ ] Main entry point runs: `python3 main.py --help`
- [ ] All src/ modules can be imported: `python3 -c "from src import *"`
- [ ] Scripts run without import errors
- [ ] Tests pass: `pytest tests/`

### Path Verification
- [ ] Config files are found: No FileNotFoundError
- [ ] SQL files are found: Database setup works
- [ ] Data files are accessible

### Functionality Verification
- [ ] Application starts successfully
- [ ] Database connections work
- [ ] API calls succeed
- [ ] Core features function correctly
- [ ] No regression in existing functionality

### Git Verification
- [ ] All changes committed
- [ ] No sensitive files tracked
- [ ] .gitignore updated correctly
- [ ] Git status is clean

### Documentation Verification
- [ ] README updated with new structure
- [ ] Setup instructions reflect new paths
- [ ] Import examples are correct
- [ ] Migration guide created (optional)

---

## 📚 Best Practices Summary

### Do's ✅
- ✅ Use git mv for tracked files
- ✅ Test imports after each major change
- ✅ Use relative imports within src/ package (`.module`)
- ✅ Use absolute imports from outside src/ (`from src.module`)
- ✅ Use pathlib.Path for file paths
- ✅ Update .gitignore for sensitive config files
- ✅ Keep entry points in root
- ✅ Commit changes incrementally
- ✅ Run tests after reorganization
- ✅ Update documentation

### Don'ts ❌
- ❌ Don't move entry points (main.py) to src/
- ❌ Don't move existing organized directories
- ❌ Don't use hardcoded file paths
- ❌ Don't mix relative and absolute imports in same file
- ❌ Don't commit sensitive files in config/
- ❌ Don't forget to update tests
- ❌ Don't skip verification steps
- ❌ Don't move files without updating imports
- ❌ Don't reorganize without testing

---

## 🎓 Example: Complete Reorganization Session

Here's a complete example of reorganizing a project:

```bash
# 1. Analyze current structure
echo "=== Current Python files in root ==="
ls -1 *.py

# 2. Create new directories
mkdir -p src config sql
echo '"""Core modules"""' > src/__init__.py

# 3. Move files using git
git mv database.py api.py models.py utils.py config.py src/
mv settings.json credentials.json keywords.json config/
git mv schema.sql views.sql sql/

# 4. Update main.py imports
sed -i '' 's/^from database import/from src.database import/g' main.py
sed -i '' 's/^from api import/from src.api import/g' main.py
sed -i '' 's/^from models import/from src.models import/g' main.py
sed -i '' 's/^from config import/from src.config import/g' main.py

# 5. Update imports in src/ modules
cd src
for file in *.py; do
    sed -i '' 's/^from database import/from .database import/g' "$file"
    sed -i '' 's/^from api import/from .api import/g' "$file"
    sed -i '' 's/^from models import/from .models import/g' "$file"
    sed -i '' 's/^from config import/from .config import/g' "$file"
    sed -i '' 's/^from utils import/from .utils import/g' "$file"
done
cd ..

# 6. Update scripts/
find scripts -name "*.py" -exec sed -i '' 's/^from database import/from src.database import/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/^from api import/from src.api import/g' {} \;
find scripts -name "*.py" -exec sed -i '' 's/^from config import/from src.config import/g' {} \;

# 7. Update tests/
find tests -name "*.py" -exec sed -i '' 's/^from database import/from src.database import/g' {} \;
find tests -name "*.py" -exec sed -i '' 's/^from api import/from src.api import/g' {} \;

# 8. Update config file paths
sed -i '' "s|'settings\.json'|'config/settings.json'|g" src/*.py
sed -i '' "s|'keywords\.json'|'config/keywords.json'|g" src/*.py

# 9. Test imports
python3 -c "from src.database import Database; print('✅ Imports work!')"
python3 main.py --help

# 10. Run tests
pytest tests/

# 11. Update .gitignore
cat >> .gitignore << 'EOF'

# Config - sensitive files
config/credentials.json
config/*.key
config/secrets.*

# Python cache
src/__pycache__/
EOF

# 12. Commit changes
git add src/ config/ sql/ main.py scripts/ tests/ .gitignore
git commit -m "Reorganize project structure for better maintainability"

# 13. Verify
git status
ls -la
echo "✅ Reorganization complete!"
```

---

## 📞 Support & Troubleshooting

### If something breaks:

1. **Check the error message** - It usually tells you what's wrong
2. **Verify working directory** - Run from project root
3. **Check import paths** - Make sure they match new structure
4. **Use git diff** - See what changed: `git diff HEAD~1`
5. **Rollback if needed** - `git reset --hard HEAD~1`

### Need to revert?

```bash
# See what changed
git log --oneline -5

# Revert last commit
git revert HEAD

# Or reset (destructive)
git reset --hard HEAD~1
```

---

## 🎉 Success Criteria

Your reorganization is successful when:

✅ Root directory only has entry points and documentation
✅ All core modules are in src/ package
✅ All config files are in config/ directory
✅ All SQL files are in sql/ directory
✅ All imports work correctly
✅ All tests pass
✅ Application runs without errors
✅ No functionality is broken
✅ Documentation is updated
✅ Changes are committed to git

---

**Generated from successful reorganization of PNCP Medical Data Processor**
**Date: November 5, 2025**
