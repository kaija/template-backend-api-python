# Database Migrations Guide

This guide covers database migration management using Alembic with comprehensive safety features, testing, and rollback procedures.

## Overview

Our migration system provides:
- **Auto-generation** of migrations from model changes
- **Safe rollback** procedures with data backup
- **Migration testing** and validation
- **Production safety** checks
- **Comprehensive logging** and error handling

## Quick Start

### Basic Commands

```bash
# Upgrade to latest version
make migrate-up

# Check current revision
make migrate-current

# Check for pending migrations
make migrate-check

# Create new migration
make migrate-new MSG="Add user preferences table"
```

### Using Python Scripts Directly

```bash
# Upgrade database
python scripts/migrate.py upgrade

# Create new migration with autogenerate
python scripts/migrate.py revision -m "Add new feature"

# Check migration status
python scripts/migrate.py check
```

## Migration Workflow

### 1. Development Workflow

1. **Modify Models**: Update your SQLAlchemy models in `src/database/models.py`

2. **Generate Migration**: Create a new migration file
   ```bash
   make migrate-new MSG="Add user preferences table"
   ```

3. **Review Migration**: Check the generated migration file in `migrations/versions/`

4. **Test Migration**: Test the migration locally
   ```bash
   make migrate-test
   ```

5. **Apply Migration**: Apply to development database
   ```bash
   make migrate-up
   ```

### 2. Production Deployment

1. **Backup Database**: Always create a backup before production migrations
   ```bash
   make migrate-backup
   ```

2. **Validate Migration**: Check migration safety
   ```bash
   make migrate-validate REV=head
   ```

3. **Production Check**: Run production safety checks
   ```bash
   make migrate-prod-check
   ```

4. **Apply Migration**: Apply with monitoring
   ```bash
   make migrate-up
   ```

## Migration Scripts

### migrate.py

Main migration management script with the following commands:

- `upgrade [revision]` - Upgrade to specified revision (default: head)
- `downgrade <revision>` - Downgrade to specified revision
- `current` - Show current revision
- `history [-v]` - Show migration history
- `revision -m <message>` - Create new migration
- `check` - Check for pending migrations
- `test [revision]` - Test migration up/down cycle

### rollback.py

Safe rollback management with backup functionality:

- `rollback <revision>` - Perform safe rollback with backup
- `validate <revision>` - Validate rollback safety
- `backup [--name]` - Create data backup
- `list-backups` - List available backups
- `show-backup <file>` - Show backup information

## Configuration

### Alembic Configuration

The `alembic.ini` file is configured to:
- Use dynamic database URL from application settings
- Enable auto-formatting with Black
- Support both online and offline migrations
- Include comprehensive logging

### Environment Configuration

The `migrations/env.py` file provides:
- **Automatic model detection** from `src.database.models`
- **Fallback configuration** for different environments
- **SQLite compatibility** with batch operations
- **Comprehensive error handling**
- **Custom object filtering** for autogenerate

## Safety Features

### 1. Production Safety Checks

- **Environment detection** - Warns when running in production
- **Confirmation prompts** - Requires explicit confirmation for dangerous operations
- **Data validation** - Checks for existing data before destructive operations

### 2. Backup System

Automatic backup creation before rollbacks:
```bash
# Create manual backup
make migrate-backup

# List available backups
make migrate-list-backups

# Show backup details
make migrate-show-backup BACKUP=backup_file.json
```

### 3. Rollback Validation

Before performing rollbacks, the system:
- Validates target revision exists
- Checks for potentially destructive operations
- Analyzes data loss risk
- Creates comprehensive validation reports

## Testing

### Unit Tests

Run migration tests:
```bash
pytest tests/test_migrations.py -v
```

Test coverage includes:
- Migration upgrade/downgrade cycles
- Table structure validation
- Data integrity checks
- Autogenerate functionality

### Integration Testing

Test migrations with application models:
```bash
python scripts/migrate.py test
```

This performs:
1. Upgrade to head
2. Downgrade to base
3. Upgrade back to head
4. Validation of each step

## Common Operations

### Creating Migrations

#### Auto-generate from Model Changes
```bash
# After modifying models
make migrate-new MSG="Add user avatar field"
```

#### Manual Migration
```bash
# Create empty migration for custom operations
python scripts/migrate.py revision -m "Custom data migration" --no-autogenerate
```

### Applying Migrations

#### Development
```bash
# Apply all pending migrations
make migrate-up

# Apply to specific revision
python scripts/migrate.py upgrade 001
```

#### Production
```bash
# Full production workflow
make migrate-backup
make migrate-validate REV=head
make migrate-prod-check
make migrate-up
```

### Rolling Back

#### Safe Rollback with Backup
```bash
# Rollback to specific revision
make migrate-rollback REV=001
```

#### Emergency Rollback
```bash
# Force rollback (skip safety checks)
python scripts/rollback.py rollback 001 --force
```

## Troubleshooting

### Common Issues

#### 1. Migration Conflicts
```bash
# Check current state
make migrate-current

# View history
make migrate-history

# Resolve conflicts by merging or rebasing migrations
```

#### 2. Failed Migrations
```bash
# Check what went wrong
make migrate-current

# Manual fix and stamp
python scripts/migrate.py stamp <revision>
```

#### 3. Database Out of Sync
```bash
# Reset development database
make migrate-reset-dev

# Or stamp to current model state
python scripts/migrate.py stamp head
```

### Recovery Procedures

#### 1. Restore from Backup
```bash
# List available backups
make migrate-list-backups

# Show backup details
make migrate-show-backup BACKUP=rollback_backup_20240101_120000.json

# Manual restore process (database-specific)
```

#### 2. Manual Schema Sync
```bash
# Generate migration to sync with current models
make migrate-new MSG="Sync schema with models"

# Review and apply
make migrate-up
```

## Best Practices

### 1. Migration Development

- **Always review** generated migrations before applying
- **Test migrations** in development environment first
- **Use descriptive messages** for migration names
- **Keep migrations small** and focused on single changes
- **Avoid data migrations** in schema migrations when possible

### 2. Production Deployments

- **Always backup** before production migrations
- **Test in staging** environment first
- **Plan maintenance windows** for large migrations
- **Monitor application** during and after migrations
- **Have rollback plan** ready

### 3. Team Collaboration

- **Coordinate migrations** with team members
- **Resolve conflicts** before merging
- **Document complex migrations** with comments
- **Share migration plans** for review

## Advanced Usage

### Custom Migration Operations

```python
# In migration file
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Custom data migration
    connection = op.get_bind()
    connection.execute(
        "UPDATE user SET status = 'ACTIVE' WHERE status IS NULL"
    )

def downgrade():
    # Reverse operation
    pass
```

### Batch Operations for SQLite

```python
# For SQLite compatibility
def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('new_field', sa.String(50)))
```

### Environment-Specific Migrations

```python
# Check environment in migration
from src.config.settings import is_production

def upgrade():
    if not is_production():
        # Development-only changes
        pass
```

## Monitoring and Logging

### Migration Logs

All migration operations are logged with:
- **Timestamp** and **user** information
- **Command executed** and **parameters**
- **Success/failure** status
- **Error details** if applicable

### Health Checks

Monitor migration status:
```bash
# Check if database is up to date
make migrate-check

# Get current revision
make migrate-current
```

## Security Considerations

### 1. Sensitive Data

- **Never include** sensitive data in migrations
- **Use environment variables** for configuration
- **Mask sensitive information** in logs

### 2. Access Control

- **Limit migration access** to authorized personnel
- **Use separate credentials** for migrations if possible
- **Audit migration activities** in production

### 3. Backup Security

- **Encrypt backups** containing sensitive data
- **Store backups securely** with appropriate access controls
- **Regularly test** backup restoration procedures

## Integration with CI/CD

### Automated Testing

```yaml
# Example GitHub Actions workflow
- name: Test Migrations
  run: |
    python scripts/migrate.py upgrade
    pytest tests/test_migrations.py
    python scripts/migrate.py test
```

### Deployment Pipeline

```yaml
# Production deployment
- name: Backup Database
  run: python scripts/rollback.py backup

- name: Run Migrations
  run: python scripts/migrate.py upgrade

- name: Verify Migration
  run: python scripts/migrate.py check
```

## Support and Maintenance

### Regular Maintenance

- **Review migration history** periodically
- **Clean up old backups** based on retention policy
- **Update migration scripts** as needed
- **Monitor migration performance** and optimize if necessary

### Getting Help

- Check the **troubleshooting section** above
- Review **migration logs** for error details
- Test in **development environment** first
- Contact the **development team** for complex issues