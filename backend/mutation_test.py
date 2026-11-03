"""Mutation testing script for CRM-Splash backend."""
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

# Mutation operators to apply
MUTATIONS: list[tuple[str, str, str, str]] = [
    # (file_path, old_pattern, new_pattern, description)
    (
        "src/core/security.py",
        r"return _pwd_context\.verify\(plain, hashed\)",
        "return True  # MUTANT: always accept password",
        "verify_password always returns True",
    ),
    (
        "src/core/security.py",
        r"raise UnauthorizedError\(\"invalid or expired token\"",
        "return {'sub': 'admin', 'org': 'demo', 'role': 'admin'}  # MUTANT: bypass JWT validation",
        "decode_access_token bypasses validation",
    ),
    (
        "src/core/rbac.py",
        r"if not role_has\(role, permission\):\s+raise ForbiddenError\(",
        "if False:  # MUTANT: allow all permissions\n        raise ForbiddenError(",
        "require_permission allows everything",
    ),
    (
        "src/core/tenant.py",
        r"if value is None:\s+raise OrganizationBoundaryError\(",
        "if False:  # MUTANT: return None as org\n        raise OrganizationBoundaryError(",
        "current_org_id returns None without raising",
    ),
    (
        "src/modules/contacts/service.py",
        r"if not c:\s+raise NotFoundError\(f\"contact \{contact_id\} not found\"\)",
        "if False:  # MUTANT: skip existence check\n            raise NotFoundError(f\"contact {contact_id} not found\")",
        "get_contact skips existence check",
    ),
    (
        "src/modules/opportunities/service.py",
        r"if data\.estimated_value is not None or data\.probability is not None:",
        "if False:  # MUTANT: skip weighted value recalculation",
        "update_opportunity skips weighted_value recalculation",
    ),
    (
        "src/modules/users/service.py",
        r"if not verify_password\(payload\.password, user\.password_hash\):",
        "if False:  # MUTANT: skip password check",
        "login skips password verification",
    ),
    (
        "src/core/config.py",
        r"if self\.jwt_secret == DEFAULT_JWT_SECRET:",
        "if False:  # MUTANT: allow default secrets in prod",
        "Settings allows default JWT secret in production",
    ),
    (
        "src/modules/automations/engine.py",
        r"AutomationRule\.is_active\.is_\(True\),",
        "# MUTANT: include inactive rules\n                AutomationRule.is_active.is_(False),",
        "AutomationEngine includes inactive rules",
    ),
    (
        "src/modules/opportunities/service.py",
        r"if stage\.pipeline_id != data\.pipeline_id:",
        "if False:  # MUTANT: skip stage-pipeline validation",
        "create_opportunity skips stage-pipeline validation",
    ),
    (
        "src/core/pagination.py",
        r"return \(self\.page - 1\) \* self\.page_size",
        "return self.page * self.page_size  # MUTANT: off-by-one in offset",
        "PageParams.offset off-by-one (page 2 starts at 2*page_size)",
    ),
]


def apply_mutation(file_path: str, old_pattern: str, new_pattern: str) -> tuple[bool, str]:
    """Apply a mutation to a file. Returns (success, original_content)."""
    path = Path(file_path)
    if not path.exists():
        return False, ""
    
    original = path.read_text()
    mutated = re.sub(old_pattern, new_pattern, original, count=1)
    
    if mutated == original:
        return False, original
    
    path.write_text(mutated)
    return True, original


def restore_file(file_path: str, original: str) -> None:
    """Restore original file content."""
    Path(file_path).write_text(original)


def run_tests() -> tuple[bool, str]:
    """Run pytest and return (passed, output)."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )
    return result.returncode == 0, result.stdout + result.stderr


def main():
    print("=" * 70)
    print("MUTATION TESTING - CRM-Splash Backend")
    print("=" * 70)
    print()
    
    # First verify tests pass on clean code
    print("1. Verifying baseline (clean code)...")
    passed, output = run_tests()
    if not passed:
        print("❌ Baseline tests failed. Cannot proceed with mutation testing.")
        print(output)
        sys.exit(1)
    print("✅ Baseline tests pass\n")
    
    results = []
    total_mutations = len(MUTATIONS)
    
    print(f"2. Running {total_mutations} mutations...\n")
    
    for i, (file_path, old_pattern, new_pattern, description) in enumerate(MUTATIONS, 1):
        print(f"[{i}/{total_mutations}] {description}")
        print(f"    File: {file_path}")
        
        # Apply mutation
        success, original = apply_mutation(file_path, old_pattern, new_pattern)
        
        if not success:
            print("    ⚠️  Pattern not found, skipping\n")
            results.append(("SKIPPED", description, file_path))
            continue
        
        try:
            # Run tests against mutated code
            passed, output = run_tests()
            
            if passed:
                print(f"    ❌ SURVIVED - Tests did not catch this mutation!")
                print(f"    ⚠️  CRITICAL: {description}")
                results.append(("SURVIVED", description, file_path))
            else:
                print(f"    ✅ KILLED - Tests detected the mutation")
                results.append(("KILLED", description, file_path))
        finally:
            # Always restore original
            restore_file(file_path, original)
        
        print()
    
    # Summary
    print("=" * 70)
    print("MUTATION TESTING RESULTS")
    print("=" * 70)
    
    killed = sum(1 for r in results if r[0] == "KILLED")
    survived = sum(1 for r in results if r[0] == "SURVIVED")
    skipped = sum(1 for r in results if r[0] == "SKIPPED")
    
    print(f"\nTotal mutations: {total_mutations}")
    print(f"Killed: {killed}")
    print(f"Survived: {survived}")
    print(f"Skipped: {skipped}")
    
    if killed + survived > 0:
        mutation_score = (killed / (killed + survived)) * 100
        print(f"\nMutation Score: {mutation_score:.1f}%")
        
        if mutation_score >= 80:
            print("✅ EXCELLENT - Test suite is strong")
        elif mutation_score >= 60:
            print("⚠️  GOOD - Test suite has room for improvement")
        else:
            print("❌ POOR - Test suite needs significant work")
    
    if survived > 0:
        print("\n" + "=" * 70)
        print("CRITICAL: Surviving Mutations (Test Gaps)")
        print("=" * 70)
        for status, description, file_path in results:
            if status == "SURVIVED":
                print(f"\n❌ {description}")
                print(f"   File: {file_path}")
                print(f"   → Tests do not verify this behavior")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
