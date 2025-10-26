"""Shared permission helpers for workspace resources."""

from __future__ import annotations

from fastapi import HTTPException, status

from ..models import Project, User

# Roles that can manage the entire workspace regardless of project ownership.
MANAGER_ROLES: set[str] = {"admin", "super_admin"}


def can_manage_workspace(user: User) -> bool:
    """Return ``True`` when the user has elevated workspace permissions."""

    return user.role in MANAGER_ROLES


def ensure_project_access(project: Project | None, user: User) -> Project:
    """Ensure the user can access the given project.

    The helper raises :class:`HTTPException` if the project is missing or the
    user lacks sufficient permissions.
    """

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.created_by != user.user_id and not can_manage_workspace(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return project


def restrict_projects_query(query, user: User):
    """Limit a SQLAlchemy query to projects owned by the user when required."""

    if can_manage_workspace(user):
        return query
    return query.filter(Project.created_by == user.user_id)
