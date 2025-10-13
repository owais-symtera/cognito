#!/usr/bin/env python3
"""
Infrastructure validation script for CognitoAI Engine monorepo structure.

Validates that the monorepo is correctly structured according to pharmaceutical
intelligence platform requirements and architectural standards.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import os
import json
from pathlib import Path


def validate_monorepo_structure():
    """
    Validate complete monorepo structure for pharmaceutical compliance.

    Checks all required directories, configuration files, and project setup
    according to CognitoAI Engine architectural requirements.

    Returns:
        bool: True if structure is valid, False otherwise
    """
    print("Validating CognitoAI Engine monorepo structure...")

    # Define required structure
    required_structure = {
        "root_files": [
            "package.json", "turbo.json", ".env.example"
        ],
        "backend_structure": [
            "apps/backend/src/main.py",
            "apps/backend/requirements.txt",
            "apps/backend/requirements-dev.txt",
            "apps/backend/pytest.ini",
            "apps/backend/src/core",
            "apps/backend/src/integrations",
            "apps/backend/src/database",
            "apps/backend/src/api",
            "apps/backend/src/schemas",
            "apps/backend/src/background",
            "apps/backend/src/config",
            "apps/backend/src/utils",
            "apps/backend/tests"
        ],
        "frontend_structure": [
            "apps/frontend/package.json",
            "apps/frontend/next.config.js",
            "apps/frontend/tailwind.config.js",
            "apps/frontend/src/app/layout.tsx",
            "apps/frontend/src/app/page.tsx",
            "apps/frontend/src/app/globals.css",
            "apps/frontend/src/components",
            "apps/frontend/src/hooks",
            "apps/frontend/src/stores",
            "apps/frontend/src/lib",
            "apps/frontend/tests"
        ],
        "shared_packages": [
            "packages/shared-types/src/index.ts",
            "packages/shared-types/package.json",
            "packages/api-contracts",
            "packages/testing-utils"
        ]
    }

    validation_passed = True

    # Validate root files
    print("\nValidating root configuration files...")
    for file in required_structure["root_files"]:
        if os.path.exists(file):
            print(f"  PASS {file}")
        else:
            print(f"  FAIL {file} - MISSING")
            validation_passed = False

    # Validate backend structure
    print("\nValidating backend structure...")
    for path in required_structure["backend_structure"]:
        if os.path.exists(path):
            print(f"  PASS {path}")
        else:
            print(f"  FAIL {path} - MISSING")
            validation_passed = False

    # Validate frontend structure
    print("\nValidating frontend structure...")
    for path in required_structure["frontend_structure"]:
        if os.path.exists(path):
            print(f"  PASS {path}")
        else:
            print(f"  FAIL {path} - MISSING")
            validation_passed = False

    # Validate shared packages
    print("\nValidating shared packages...")
    for path in required_structure["shared_packages"]:
        if os.path.exists(path):
            print(f"  PASS {path}")
        else:
            print(f"  FAIL {path} - MISSING")
            validation_passed = False

    return validation_passed


def validate_configuration_files():
    """
    Validate configuration file contents for pharmaceutical compliance.

    Checks that configuration files contain required pharmaceutical
    intelligence platform settings and compliance requirements.

    Returns:
        bool: True if configurations are valid, False otherwise
    """
    print("\nValidating configuration file contents...")

    config_valid = True

    # Validate package.json
    try:
        with open("package.json", "r") as f:
            package_config = json.load(f)

        required_package_fields = ["name", "workspaces", "scripts", "devDependencies"]
        for field in required_package_fields:
            if field in package_config:
                print(f"  PASS package.json has '{field}'")
            else:
                print(f"  FAIL package.json missing '{field}'")
                config_valid = False

        # Check workspaces configuration
        if "workspaces" in package_config:
            workspaces = package_config["workspaces"]
            if "apps/*" in workspaces and "packages/*" in workspaces:
                print(f"  ✅ Turborepo workspaces configured correctly")
            else:
                print(f"  ❌ Workspaces not configured for monorepo")
                config_valid = False

    except FileNotFoundError:
        print("  ❌ package.json not found")
        config_valid = False
    except json.JSONDecodeError:
        print("  ❌ package.json invalid JSON")
        config_valid = False

    # Validate turbo.json
    try:
        with open("turbo.json", "r") as f:
            turbo_config = json.load(f)

        if "pipeline" in turbo_config:
            print(f"  ✅ turbo.json has pipeline configuration")

            required_tasks = ["build", "dev", "test", "lint"]
            pipeline = turbo_config["pipeline"]
            for task in required_tasks:
                if task in pipeline:
                    print(f"  ✅ Turbo pipeline includes '{task}' task")
                else:
                    print(f"  ❌ Turbo pipeline missing '{task}' task")
                    config_valid = False
        else:
            print(f"  ❌ turbo.json missing pipeline configuration")
            config_valid = False

    except FileNotFoundError:
        print("  ❌ turbo.json not found")
        config_valid = False
    except json.JSONDecodeError:
        print("  ❌ turbo.json invalid JSON")
        config_valid = False

    return config_valid


def validate_pharmaceutical_compliance():
    """
    Validate pharmaceutical compliance features in the codebase.

    Checks that the structure includes all required pharmaceutical
    intelligence and regulatory compliance components.

    Returns:
        bool: True if compliance features are present, False otherwise
    """
    print("\n💊 Validating pharmaceutical compliance features...")

    compliance_valid = True

    # Check for audit trail capabilities
    audit_components = [
        "apps/backend/src/core",  # Core business logic
        "apps/backend/src/database",  # Database layer for audit trails
    ]

    for component in audit_components:
        if os.path.exists(component):
            print(f"  ✅ Audit trail component: {component}")
        else:
            print(f"  ❌ Missing audit component: {component}")
            compliance_valid = False

    # Check for source tracking capabilities
    source_tracking_components = [
        "apps/backend/src/integrations",  # External API integrations
        "packages/shared-types/src/index.ts"  # Source reference types
    ]

    for component in source_tracking_components:
        if os.path.exists(component):
            print(f"  ✅ Source tracking component: {component}")
        else:
            print(f"  ❌ Missing source tracking component: {component}")
            compliance_valid = False

    # Validate shared types include pharmaceutical compliance types
    try:
        with open("packages/shared-types/src/index.ts", "r") as f:
            types_content = f.read()

        pharmaceutical_types = [
            "DrugRequest", "CategoryResult", "SourceReference",
            "SourceConflict", "VerificationStatus"
        ]

        for type_name in pharmaceutical_types:
            if type_name in types_content:
                print(f"  ✅ Pharmaceutical type defined: {type_name}")
            else:
                print(f"  ❌ Missing pharmaceutical type: {type_name}")
                compliance_valid = False

    except FileNotFoundError:
        print("  ❌ Shared types file not found")
        compliance_valid = False

    return compliance_valid


def main():
    """
    Main validation function for CognitoAI Engine infrastructure.

    Runs complete infrastructure validation including structure,
    configuration, and pharmaceutical compliance requirements.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    print("CognitoAI Engine Infrastructure Validation")
    print("=" * 60)

    structure_valid = validate_monorepo_structure()
    config_valid = validate_configuration_files()
    compliance_valid = validate_pharmaceutical_compliance()

    print("\n" + "=" * 60)

    if structure_valid and config_valid and compliance_valid:
        print("🎉 VALIDATION PASSED: Infrastructure ready for pharmaceutical intelligence platform!")
        print("\n✅ Monorepo structure: VALID")
        print("✅ Configuration files: VALID")
        print("✅ Pharmaceutical compliance: VALID")
        print("\n🔬 Ready for pharmaceutical intelligence processing development!")
        return 0
    else:
        print("❌ VALIDATION FAILED: Infrastructure issues detected!")
        print(f"\n{'✅' if structure_valid else '❌'} Monorepo structure: {'VALID' if structure_valid else 'INVALID'}")
        print(f"{'✅' if config_valid else '❌'} Configuration files: {'VALID' if config_valid else 'INVALID'}")
        print(f"{'✅' if compliance_valid else '❌'} Pharmaceutical compliance: {'VALID' if compliance_valid else 'INVALID'}")
        print("\n🔧 Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    exit(main())