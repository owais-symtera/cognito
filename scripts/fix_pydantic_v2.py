"""Fix Pydantic v2 compatibility issues"""

import os
from pathlib import Path

def fix_pydantic_configs():
    """Fix all Pydantic v2 config issues in schemas"""

    schemas_dir = Path("apps/backend/src/schemas")

    fixes = {
        "categories.py": [
            ("orm_mode = True", "from_attributes = True"),
            ("schema_extra = {", "json_schema_extra = {")
        ],
        "analysis.py": [
            ("schema_extra = {", "json_schema_extra = {"),
            ("orm_mode = True", "from_attributes = True")
        ],
        "status.py": [
            ("orm_mode = True", "from_attributes = True"),
            ("schema_extra = {", "json_schema_extra = {")
        ],
        "api_providers.py": [
            ("orm_mode = True", "from_attributes = True")
        ]
    }

    for filename, replacements in fixes.items():
        file_path = schemas_dir / filename
        if file_path.exists():
            print(f"Fixing {file_path}")
            content = file_path.read_text()

            for old, new in replacements:
                if old in content:
                    content = content.replace(old, new)
                    print(f"  - Replaced '{old}' with '{new}'")

            file_path.write_text(content)
            print(f"  ✓ {filename} updated")
        else:
            print(f"  ⚠ {filename} not found")

if __name__ == "__main__":
    fix_pydantic_configs()
    print("\n✅ Pydantic v2 compatibility fixes applied!")