# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import csv
import secrets
from datetime import date
from pathlib import Path
from typing import Any

from django.core.management import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.core.exceptions import ValidationError

from plane.db.models import Profile, User, Workspace, WorkspaceMember


REQUIRED_COLUMNS = {"email", "username", "first_name"}
VALID_WORKSPACE_ROLES = {5, 15, 20}


class Command(BaseCommand):
    help = "Import users from a UTF-8 CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the UTF-8 CSV file")
        parser.add_argument(
            "--workspace-slug",
            type=str,
            help="Existing workspace to assign imported users to",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the CSV without changing the database",
        )

    def handle(self, *args: Any, **options: Any):
        csv_path = Path(options["csv_path"])
        workspace_slug = self._clean(options.get("workspace_slug"))
        dry_run = options["dry_run"]

        if not csv_path.is_file():
            raise CommandError(f"CSV file does not exist: {csv_path}")

        workspace = None
        if workspace_slug:
            workspace = Workspace.objects.filter(slug=workspace_slug).first()
            if workspace is None:
                raise CommandError(f"Workspace does not exist: {workspace_slug}")

        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                self._validate_columns(reader.fieldnames)
                rows = list(reader)
        except UnicodeDecodeError as error:
            raise CommandError("CSV must be UTF-8 encoded") from error
        except csv.Error as error:
            raise CommandError(f"Invalid CSV: {error}") from error

        if not rows:
            raise CommandError("CSV file has no data rows")

        summary = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
        seen_emails: set[str] = set()
        seen_usernames: set[str] = set()

        try:
            with transaction.atomic():
                for row_number, raw_row in enumerate(rows, start=2):
                    row = {key.strip(): (value or "").strip() for key, value in raw_row.items() if key}
                    try:
                        email = self._required(row, "email", row_number).lower()
                        username = self._required(row, "username", row_number)
                        first_name = self._required(row, "first_name", row_number)
                        self._validate_email(email, row_number)

                        if email in seen_emails:
                            raise CommandError(f"duplicate email in CSV: {email}")
                        if username in seen_usernames:
                            raise CommandError(f"duplicate username in CSV: {username}")
                        seen_emails.add(email)
                        seen_usernames.add(username)

                        target_workspace = workspace
                        row_workspace_slug = self._clean(row.get("workspace_slug"))
                        if row_workspace_slug:
                            if workspace_slug and row_workspace_slug != workspace_slug:
                                raise CommandError("workspace_slug conflicts with --workspace-slug")
                            target_workspace = Workspace.objects.filter(slug=row_workspace_slug).first()
                            if target_workspace is None:
                                raise CommandError(f"workspace does not exist: {row_workspace_slug}")

                        role = self._workspace_role(row.get("workspace_role"), row_number)
                        existing_user = User.objects.filter(email=email).first()
                        username_owner = User.objects.filter(username=username).exclude(email=email).exists()
                        if username_owner:
                            raise CommandError(f"username already belongs to another user: {username}")

                        if existing_user is None:
                            user = User(
                                email=email,
                                username=username,
                                first_name=first_name,
                                last_name=self._clean(row.get("last_name")),
                                mssv=self._clean(row.get("mssv")),
                                chuc_vu=self._clean(row.get("chuc_vu")),
                                ngay_sinh=self._date(row.get("ngay_sinh"), row_number),
                                is_active=True,
                                is_email_verified=True,
                            )
                            password = self._clean(row.get("initial_password")) or secrets.token_urlsafe(18)
                            user.set_password(password)
                            user.is_password_reset_required = not bool(self._clean(row.get("initial_password")))
                            action = "created"
                        else:
                            user = existing_user
                            user.username = username
                            user.first_name = first_name
                            user.last_name = self._clean(row.get("last_name"))
                            user.mssv = self._clean(row.get("mssv"))
                            user.chuc_vu = self._clean(row.get("chuc_vu"))
                            user.ngay_sinh = self._date(row.get("ngay_sinh"), row_number)
                            user.is_active = True
                            action = "updated"

                        if not dry_run:
                            user.save()
                            Profile.objects.get_or_create(user=user)
                            if target_workspace:
                                WorkspaceMember.objects.update_or_create(
                                    workspace=target_workspace,
                                    member=user,
                                    defaults={"role": role, "is_active": True},
                                )

                        summary[action] += 1
                        self.stdout.write(f"row {row_number}: {action} {email}")
                    except (CommandError, ValidationError, ValueError) as error:
                        summary["failed"] += 1
                        raise CommandError(f"row {row_number}: {error}") from error

                if dry_run:
                    transaction.set_rollback(True)
        except CommandError:
            raise

        mode = "validated" if dry_run else "imported"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {summary}"))

    @staticmethod
    def _clean(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def _required(row: dict[str, str], key: str, row_number: int) -> str:
        value = row.get(key, "").strip()
        if not value:
            raise CommandError(f"missing required column value: {key}")
        return value

    @staticmethod
    def _validate_columns(fieldnames: list[str] | None):
        columns = {field.strip() for field in fieldnames or [] if field}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise CommandError(f"missing required CSV columns: {', '.join(sorted(missing))}")

    @staticmethod
    def _validate_email(email: str, row_number: int):
        try:
            validate_email(email)
        except ValidationError as error:
            raise CommandError(f"invalid email: {email}") from error

    @staticmethod
    def _date(value: str, row_number: int) -> date | None:
        value = (value or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise CommandError(f"invalid ngay_sinh, expected YYYY-MM-DD: {value}") from error

    @staticmethod
    def _workspace_role(value: str | None, row_number: int) -> int:
        value = (value or "5").strip()
        try:
            role = int(value)
        except ValueError as error:
            raise CommandError(f"workspace_role must be one of 5, 15, 20: {value}") from error
        if role not in VALID_WORKSPACE_ROLES:
            raise CommandError(f"workspace_role must be one of 5, 15, 20: {value}")
        return role
