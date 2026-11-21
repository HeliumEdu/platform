from django.core.management.base import BaseCommand, CommandError
from django.db import migrations
from django.db.migrations.loader import MigrationLoader
from django.db.models import NOT_PROVIDED
from django_migration_linter import MigrationLinter

_CHECKED_AFTER = {'helium_auth': '0082', 'helium_common': '0007', 'feed': '0017', 'planner': '0089'}

_APPROVED_MIGRATIONS = set()

# On SQLite, Django rebuilds a table to alter any existing column, which trips these on every column change;
# _not_null_violations covers the NOT NULL case from the operations instead.
_LINTER_CHECKS_UNRELIABLE_ON_SQLITE = ['NOT_NULL', 'ALTER_COLUMN']


class Command(BaseCommand):
    help = ("Fail when a migration added after the baseline is unsafe to apply while the previous release still "
            "serves traffic. Approve a deliberate later-release drop by adding it to _APPROVED_MIGRATIONS.")

    def handle(self, *args, **options):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        checked = {key: migration for key, migration in loader.disk_migrations.items()
                   if migration.__module__.startswith('helium.')
                   and key[1][:4] > _CHECKED_AFTER.get(key[0], '0000')
                   and f'{key[0]}.{key[1]}' not in _APPROVED_MIGRATIONS}
        if not checked:
            self.stdout.write('No migrations after the baseline to check.')
            return

        linter = MigrationLinter(exclude_migration_tests=_LINTER_CHECKS_UNRELIABLE_ON_SQLITE)
        for key in sorted(checked):
            linter.lint_migration(linter.migration_loader.disk_migrations[key])

        violations = [violation for key, migration in checked.items()
                      for violation in _not_null_violations(migration, loader.project_state(key, at_end=False))]
        for violation in violations:
            self.stderr.write(violation)

        if linter.has_errors or violations:
            raise CommandError('Migrations are unsafe to apply while the previous release still serves traffic.')


def _not_null_violations(migration, state_before):
    violations = []
    for operation in migration.operations:
        if isinstance(operation, migrations.SeparateDatabaseAndState):
            database_operations = operation.database_operations
            violations += _unsafe_state_only_removals(migration, operation, state_before)
        else:
            database_operations = [operation]
        violations += [f'{migration.app_label}.{migration.name}: {database_operation.describe()} needs a '
                       'db_default, because the previous release omits it when inserting rows'
                       for database_operation in database_operations
                       if _requires_value_old_code_omits(database_operation, migration.app_label, state_before)]
    return violations


def _requires_value_old_code_omits(operation, app_label, state_before):
    if not isinstance(operation, (migrations.AddField, migrations.AlterField)):
        return False
    model_state = state_before.models.get((app_label, operation.model_name_lower))
    if model_state is None or operation.field.many_to_many or _accepts_omitted_value(operation.field):
        return False
    if isinstance(operation, migrations.AddField):
        return True
    field_before = model_state.fields.get(operation.name)
    return field_before is not None and _accepts_omitted_value(field_before)


def _unsafe_state_only_removals(migration, operation, state_before):
    relaxed = {(o.model_name_lower, o.name_lower) for o in operation.database_operations
               if isinstance(o, migrations.AlterField) and _accepts_omitted_value(o.field)}
    violations = []
    for state_operation in operation.state_operations:
        if (not isinstance(state_operation, migrations.RemoveField)
                or (state_operation.model_name_lower, state_operation.name_lower) in relaxed):
            continue
        field = state_before.models[migration.app_label, state_operation.model_name_lower].fields[state_operation.name]
        if not field.many_to_many and not _accepts_omitted_value(field):
            violations.append(f'{migration.app_label}.{migration.name}: {state_operation.describe()} leaves a '
                              'NOT NULL column with no db_default, so new code cannot insert rows')
    return violations


def _accepts_omitted_value(field):
    return field.null or field.db_default is not NOT_PROVIDED
