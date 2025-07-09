# 🚨 CRITICAL DATABASE RULES 🚨

## ⚠️ NEVER MANUALLY CHANGE THE DATABASE ⚠️

### RULE #1: ALL DATABASE CHANGES MUST GO THROUGH ALEMBIC
- **NEVER** run manual `ALTER TABLE` commands
- **NEVER** add columns directly with SQL
- **NEVER** modify database schema outside of Alembic migrations
- **ALWAYS** use `alembic revision` to create migration files
- **ALWAYS** use `alembic upgrade` to apply changes

### RULE #2: ALEMBIC LOCATION
- Alembic files live in `/home/peter/thanotopolis/backend/`
- Use `alembic -c /home/peter/thanotopolis/backend/alembic.ini` for commands
- Migration files go in `/home/peter/thanotopolis/backend/alembic/versions/`

### RULE #3: PROPER MIGRATION WORKFLOW
1. Update SQLAlchemy model in `app/models/models.py`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review the generated migration file
4. Test the migration: `alembic upgrade head`
5. Commit both model changes AND migration file

### RULE #4: NO SHORTCUTS
- Don't create manual SQL files
- Don't run database commands directly
- Don't skip the migration process
- Don't modify the database "just for testing"

## 🛑 VIOLATION CONSEQUENCES
- Database inconsistencies
- Migration conflicts
- Production deployment failures
- Data loss risks
- Team workflow disruption

## ✅ CORRECT PROCESS FOR UNSUBSCRIBE FIELDS
1. Model is already updated in `app/models/models.py` ✓
2. Need to create proper Alembic migration
3. Need to rollback manual changes and apply via Alembic
4. Need to test migration thoroughly

Remember: **ALEMBIC IS THE ONLY WAY TO CHANGE THE DATABASE**