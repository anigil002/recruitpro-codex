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


@router.get("/projects", response_model=List[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[ProjectRead]:
    projects = db.query(Project).filter(Project.created_by == current_user.user_id).all()
    return [
        ProjectRead(
            project_id=p.project_id,
            name=p.name,
            sector=p.sector,
            location_region=p.location_region,
            summary=p.summary,
            client=p.client,
            research_done=p.research_done,
            research_status=p.research_status,
            created_by=p.created_by,
            created_at=p.created_at,
        )
        for p in projects
    ]


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
    return ProjectRead(
        project_id=project.project_id,
        name=project.name,
        sector=project.sector,
        location_region=project.location_region,
        summary=project.summary,
        client=project.client,
        research_done=project.research_done,
        research_status=project.research_status,
        created_by=project.created_by,
        created_at=project.created_at,
    )


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> ProjectRead:
    project = db.get(Project, project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectRead(
        project_id=project.project_id,
        name=project.name,
        sector=project.sector,
        location_region=project.location_region,
        summary=project.summary,
        client=project.client,
        research_done=project.research_done,
        research_status=project.research_status,
        created_by=project.created_by,
        created_at=project.created_at,
    )


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
        setattr(project, field, value)
    db.add(project)
    return ProjectRead(
        project_id=project.project_id,
        name=project.name,
        sector=project.sector,
        location_region=project.location_region,
        summary=project.summary,
        client=project.client,
        research_done=project.research_done,
        research_status=project.research_status,
        created_by=project.created_by,
        created_at=project.created_at,
    )


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
    return [
        PositionRead(
            position_id=pos.position_id,
            project_id=pos.project_id,
            title=pos.title,
            department=pos.department,
            experience=pos.experience,
            responsibilities=pos.responsibilities or [],
            requirements=pos.requirements or [],
            location=pos.location,
            description=pos.description,
            status=pos.status,
            created_at=pos.created_at,
        )
        for pos in positions
    ]


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
        created_at=position.created_at,
    )


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
        created_at=position.created_at,
    )


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
        setattr(position, field, value)
    db.add(position)
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
        created_at=position.created_at,
    )


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
