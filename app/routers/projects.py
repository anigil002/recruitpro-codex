"""Project and position endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Position, Project
from ..schemas import (
    PositionCreate,
    PositionRead,
    PositionUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from ..services.activity import log_activity
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["projects"])


def project_to_read(project: Project) -> ProjectRead:
    return ProjectRead(
        project_id=project.project_id,
        name=project.name,
        sector=project.sector,
        location_region=project.location_region,
        summary=project.summary,
        client=project.client,
        status=project.status,
        priority=project.priority,
        department=project.department,
        tags=sorted(project.tags or []),
        team_members=sorted(project.team_members or []),
        target_hires=project.target_hires or 0,
        hires_count=project.hires_count or 0,
        research_done=project.research_done,
        research_status=project.research_status,
        created_by=project.created_by,
        created_at=project.created_at,
    )


def position_to_read(position: Position) -> PositionRead:
    return PositionRead(
        position_id=position.position_id,
        project_id=position.project_id,
        title=position.title,
        department=position.department,
        experience=position.experience,
        responsibilities=position.responsibilities or [],
        requirements=position.requirements or [],
        location=position.location,
        description=position.description,
        status=position.status,
        openings=position.openings if position.openings is not None else 0,
        applicants_count=position.applicants_count if position.applicants_count is not None else 0,
        created_at=position.created_at,
    )


@router.get("/projects", response_model=List[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[ProjectRead]:
    projects = db.query(Project).filter(Project.created_by == current_user.user_id).all()
    return [project_to_read(p) for p in projects]


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    project = Project(
        project_id=generate_id(),
        name=payload.name,
        sector=payload.sector,
        location_region=payload.location_region,
        summary=payload.summary,
        client=payload.client,
        status=payload.status or "active",
        priority=payload.priority or "medium",
        department=payload.department,
        tags=sorted(set(payload.tags or [])),
        team_members=sorted(set(payload.team_members or [])),
        target_hires=payload.target_hires or 0,
        created_by=current_user.user_id,
        created_at=datetime.utcnow(),
    )
    db.add(project)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=project.project_id,
        message=f"Created project {project.name}",
        event_type="project_created",
    )
    db.flush()
    return project_to_read(project)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> ProjectRead:
    project = db.get(Project, project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project_to_read(project)


@router.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    project = db.get(Project, project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    for field, value in payload.dict(exclude_unset=True).items():
        if field in {"tags", "team_members"}:
            value = sorted(set(value or []))
        if field == "target_hires" and value is None:
            value = 0
        if field in {"status", "priority"} and value is None:
            continue
        setattr(project, field, value)
    db.add(project)
    return project_to_read(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> None:
    project = db.get(Project, project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db.delete(project)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=project.project_id,
        message=f"Deleted project {project.name}",
        event_type="project_deleted",
    )


@router.get("/positions", response_model=List[PositionRead])
def list_positions(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[PositionRead]:
    positions = (
        db.query(Position)
        .join(Project)
        .filter(Project.created_by == current_user.user_id)
        .all()
    )
    return [position_to_read(pos) for pos in positions]


@router.post("/positions", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: PositionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PositionRead:
    project = db.get(Project, payload.project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    position = Position(
        position_id=generate_id(),
        project_id=payload.project_id,
        title=payload.title,
        department=payload.department,
        experience=payload.experience,
        responsibilities=payload.responsibilities,
        requirements=payload.requirements,
        location=payload.location,
        description=payload.description,
        status=payload.status or "draft",
        openings=payload.openings if payload.openings is not None else 1,
        created_at=datetime.utcnow(),
    )
    db.add(position)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=payload.project_id,
        position_id=position.position_id,
        message=f"Created position {position.title}",
        event_type="position_created",
    )
    db.flush()
    return position_to_read(position)


@router.get("/positions/{position_id}", response_model=PositionRead)
def get_position(
    position_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PositionRead:
    position = db.get(Position, position_id)
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    project = db.get(Project, position.project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position_to_read(position)


@router.put("/positions/{position_id}", response_model=PositionRead)
def update_position(
    position_id: str,
    payload: PositionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PositionRead:
    position = db.get(Position, position_id)
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    project = db.get(Project, position.project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    for field, value in payload.dict(exclude_unset=True).items():
        if field == "openings" and value is None:
            continue
        if field in {"responsibilities", "requirements"} and value is None:
            value = []
        setattr(position, field, value)
    db.add(position)
    return position_to_read(position)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    position = db.get(Position, position_id)
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    project = db.get(Project, position.project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    db.delete(position)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=position.project_id,
        position_id=position.position_id,
        message=f"Deleted position {position.title}",
        event_type="position_deleted",
    )
