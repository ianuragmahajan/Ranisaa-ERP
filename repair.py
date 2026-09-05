from pathlib import Path
import ast, argparse, compileall, sqlite3, sys, traceback

ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "app"))
import database as db


def syntax_check():
    files=[ROOT/"app/main.py", ROOT/"app/database.py"]
    ok=True
    for f in files:
        try:
            ast.parse(f.read_text(encoding="utf-8"))
            print("Syntax OK:", f)
        except Exception:
            ok=False
            print("SYNTAX ERROR:", f)
            print(traceback.format_exc())
    return ok


def backup_before_repair():
    print("Creating safety backup BEFORE repair...")
    result=db.encrypted_backup(include_excel=True)
    if not result:
        raise RuntimeError("Safety backup failed. Repair was NOT started.")
    print("Encrypted DB backup:", result["db"])
    print("Encrypted Excel backup:", result["excel"])
    return result


def self_fix():
    """Conservative self-repair.

    This command deliberately does NOT rewrite business data or guess at arbitrary
    Python bugs. It backs up first, applies only additive database setup already
    defined by the ERP, checks Python syntax and SQLite integrity, and reports
    application errors. This makes future upgrades recoverable without risking
    silent data corruption.
    """
    print("RANISAA ERP SAFE SELF-FIX")
    print("1/5 Syntax check")
    if not syntax_check():
        raise RuntimeError("Python syntax is broken. No application files were modified.")

    print("2/5 Safety backup")
    backup_before_repair()

    print("3/5 Additive database repair/migration")
    db.init_database()
    print("Database schema checked; existing business rows are preserved.")

    print("4/5 Database integrity")
    if not db.database_integrity():
        raise RuntimeError("DATABASE INTEGRITY CHECK FAILED. No destructive repair was attempted.")
    print("Database integrity: ok")

    print("5/5 Error-log report")
    log=ROOT/"logs"/"error.log"
    if log.exists():
        text=log.read_text(encoding="utf-8",errors="replace")
        print("Error log:", log)
        if text.strip():
            print("Existing errors are logged for diagnosis; arbitrary code was NOT auto-edited.")
        else:
            print("No logged application errors.")
    else:
        print("No error log exists.")

    print("SELF-FIX COMPLETE. Existing business data was preserved.")
    print("For a real software-code bug, the error log must be used to create a targeted patch; this tool never guesses and overwrites code.")


def check():
    print("RANISAA ERP HEALTH CHECK")
    syntax_check()
    db.init_database()
    print("Database integrity:", "ok" if db.database_integrity() else "FAILED")
    log=ROOT/"logs"/"error.log"
    print("Error log:", log if log.exists() else "not created")


def main():
    parser=argparse.ArgumentParser(description="RANISAA ERP safe repair and health tools")
    parser.add_argument("--self-fix", action="store_true", help="backup first, apply safe additive DB repair, then verify")
    parser.add_argument("--check", action="store_true", help="run health checks without modifying business data")
    args=parser.parse_args()
    if args.self_fix:
        self_fix()
    else:
        check()


if __name__=="__main__":
    try:
        main()
    except Exception:
        print(traceback.format_exc())
        raise
