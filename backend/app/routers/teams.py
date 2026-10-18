from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Team, TeamMembership, User, UserRole
from app.schemas import TeamCreate, TeamUpdate, TeamOut, TeamMembershipCreate, TeamMembershipOut
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/teams", tags=["Teams"])


@router.get("", response_model=List[TeamOut])
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List teams.
    Admins can view all teams.
    Managers and Members can view all teams to allow cross-team collaboration/assignment,
    or view their own teams. Returning all teams allows easy assignment in work items.
    """
    teams = (
        db.query(Team)
        .options(joinedload(Team.memberships).joinedload(TeamMembership.user))
        .order_by(Team.name.asc())
        .all()
    )
    return teams


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new team (Admin only)."""
    existing = db.query(Team).filter(Team.name == team_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with name '{team_in.name}' already exists.",
        )
    team = Team(name=team_in.name, description=team_in.description)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get team details and members."""
    team = (
        db.query(Team)
        .options(joinedload(Team.memberships).joinedload(TeamMembership.user))
        .filter(Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )
    return team


@router.put("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    team_in: TeamUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update team info (Admin only)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )
    if team_in.name is not None and team_in.name != team.name:
        existing = db.query(Team).filter(Team.name == team_in.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with name '{team_in.name}' already exists.",
            )
        team.name = team_in.name
    if team_in.description is not None:
        team.description = team_in.description
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a team (Admin only)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )
    # Check if any work items are assigned to this team
    if team.work_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete team with associated work items. Reassign or remove items first.",
        )
    db.delete(team)
    db.commit()
    return None


@router.post("/{team_id}/members", response_model=TeamMembershipOut, status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: int,
    member_in: TeamMembershipCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Add a user to a team (Admin only)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )
    user = db.query(User).filter(User.id == member_in.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    existing_membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.team_id == team_id, TeamMembership.user_id == member_in.user_id)
        .first()
    )
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this team.",
        )
    membership = TeamMembership(
        team_id=team_id,
        user_id=member_in.user_id,
        team_role=member_in.team_role,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Remove a user from a team (Admin only)."""
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.team_id == team_id, TeamMembership.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership record not found.",
        )
    db.delete(membership)
    db.commit()
    return None
