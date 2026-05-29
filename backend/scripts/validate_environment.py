"""
Environment validation script — run before starting the server in production.
Checks all required environment variables, connectivity, and dependencies.

Usage:
    cd backend
    python scripts/validate_environment.py
"""
import os
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_env_vars():
    """Verify critical environment variables are set."""
    errors = []
    warnings = []

    secret_key = os.environ.get("SECRET_KEY", "")
    if secret_key in ("dev-secret-key-change-in-production", "change-this-secret-key-in-production"):
        warnings.append("SECRET_KEY is using development default — change for production")
    elif not secret_key:
        errors.append("SECRET_KEY is not set")

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    llm_provider = os.environ.get("LLM_PROVIDER", "openai")
    if llm_provider == "openai" and not openai_key:
        errors.append("OPENAI_API_KEY not set but LLM_PROVIDER=openai")
    elif llm_provider == "openai" and openai_key == "REPLACE_WITH_NEW_OPENAI_KEY":
        errors.append("OPENAI_API_KEY has placeholder value — set a real key")
    if llm_provider == "anthropic" and not anthropic_key:
        errors.append("ANTHROPIC_API_KEY not set but LLM_PROVIDER=anthropic")

    phi_enc = os.environ.get("ENABLE_PHI_ENCRYPTION", "false").lower()
    phi_key = os.environ.get("PHI_ENCRYPTION_KEY", "")
    if phi_enc == "true" and not phi_key:
        errors.append("ENABLE_PHI_ENCRYPTION=true but PHI_ENCRYPTION_KEY is not set")
    elif phi_enc != "true":
        warnings.append("PHI encryption is DISABLED — enable for production (ENABLE_PHI_ENCRYPTION=true)")

    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/medical_coder.db")
    if "sqlite" in database_url:
        warnings.append("Using SQLite database — PostgreSQL recommended for production")

    return errors, warnings


def check_knowledge_base():
    """Verify knowledge base files exist."""
    issues = []
    icd10_path = Path("knowledge_base/data/icd10/icd10cm_codes.json")
    if not icd10_path.exists():
        issues.append(
            f"ICD-10 data file missing: {icd10_path} — "
            "Run: python knowledge_base/scripts/build_knowledge_base.py"
        )
    return issues


def check_dependencies():
    """Check optional but recommended dependencies."""
    warnings = []
    try:
        import scispacy  # noqa: F401
    except ImportError:
        warnings.append("scispaCy not installed — using basic English NLP (reduced accuracy)")

    try:
        import negspacy  # noqa: F401
    except ImportError:
        warnings.append("negspaCy not installed — negation detection disabled")

    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"), socket_connect_timeout=2)
        r.ping()
    except Exception:
        warnings.append("Redis not reachable — caching and task queue unavailable")

    return warnings


def main():
    print("=" * 60)
    print("AI Medical Coder — Environment Validation")
    print("=" * 60)

    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    errors, warnings = check_env_vars()
    kb_issues = check_knowledge_base()
    dep_warnings = check_dependencies()

    all_warnings = warnings + dep_warnings
    all_errors = errors + kb_issues

    for w in all_warnings:
        print(f"  WARN:  {w}")
    for e in all_errors:
        print(f"  ERROR: {e}")

    if all_errors:
        print(f"\nFailed: {len(all_errors)} error(s) found. Fix before starting.")
        sys.exit(1)
    else:
        print(f"\nOK: Environment validation passed ({len(all_warnings)} warning(s))")
        sys.exit(0)


if __name__ == "__main__":
    main()
