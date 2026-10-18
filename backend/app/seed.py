import sys
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal, engine, Base
from app.models import (
    User,
    UserRole,
    Team,
    TeamMembership,
    WorkItem,
    WorkItemStatus,
    WorkItemPriority,
    WorkItemType,
    Comment,
    ActivityLog,
)
from app.auth import get_password_hash
from app.config import settings


def seed_database():
    """Seed initial development data safely."""
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Admin account
        admin = db.query(User).filter(User.email == settings.ADMIN_INITIAL_EMAIL).first()
        if not admin:
            admin = User(
                email=settings.ADMIN_INITIAL_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_INITIAL_PASSWORD),
                full_name=settings.ADMIN_INITIAL_NAME,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Created Admin user: {admin.email}")
        else:
            print(f"Admin user already exists: {admin.email}")

        # 2. Manager account
        manager = db.query(User).filter(User.email == "manager@newtonite.io").first()
        if not manager:
            manager = User(
                email="manager@newtonite.io",
                hashed_password=get_password_hash("ManagerPass123!"),
                full_name="Sarah Connor (Engineering Manager)",
                role=UserRole.MANAGER,
                is_active=True,
            )
            db.add(manager)
            db.commit()
            db.refresh(manager)
            print(f"Created Manager user: {manager.email}")

        # 3. Member account
        member = db.query(User).filter(User.email == "member@newtonite.io").first()
        if not member:
            member = User(
                email="member@newtonite.io",
                hashed_password=get_password_hash("MemberPass123!"),
                full_name="Alex Rivera (Staff Engineer)",
                role=UserRole.MEMBER,
                is_active=True,
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            print(f"Created Member user: {member.email}")

        # 4. Member 2 account
        member2 = db.query(User).filter(User.email == "dev@newtonite.io").first()
        if not member2:
            member2 = User(
                email="dev@newtonite.io",
                hashed_password=get_password_hash("DevPass123!"),
                full_name="Devin Patel (Operations Specialist)",
                role=UserRole.MEMBER,
                is_active=True,
            )
            db.add(member2)
            db.commit()
            db.refresh(member2)
            print(f"Created Second Member user: {member2.email}")

        # 5. Teams
        team_core = db.query(Team).filter(Team.name == "Core Infrastructure").first()
        if not team_core:
            team_core = Team(
                name="Core Infrastructure",
                description="Responsible for cluster availability, cloud networking, and database reliability.",
            )
            db.add(team_core)
            db.commit()
            db.refresh(team_core)
            print("Created Team: Core Infrastructure")

        team_ops = db.query(Team).filter(Team.name == "Security & Compliance").first()
        if not team_ops:
            team_ops = Team(
                name="Security & Compliance",
                description="Oversees vulnerability management, compliance audits, and security incident response.",
            )
            db.add(team_ops)
            db.commit()
            db.refresh(team_ops)
            print("Created Team: Security & Compliance")

        # 6. Team Memberships
        for t, u, r in [
            (team_core, admin, "LEAD"),
            (team_core, manager, "LEAD"),
            (team_core, member, "MEMBER"),
            (team_ops, admin, "LEAD"),
            (team_ops, manager, "MEMBER"),
            (team_ops, member2, "MEMBER"),
        ]:
            exists = db.query(TeamMembership).filter(
                TeamMembership.team_id == t.id,
                TeamMembership.user_id == u.id,
            ).first()
            if not exists:
                m = TeamMembership(team_id=t.id, user_id=u.id, team_role=r)
                db.add(m)
        db.commit()
        print("Ensured team memberships.")

        # 7. Sample Work Items
        existing_items = db.query(WorkItem).count()
        if existing_items == 0:
            now = datetime.now(timezone.utc)
            samples = [
                WorkItem(
                    title="Database read replica replication lag alert",
                    description="Replica database in us-east region is reporting 140s replication lag during peak batch ingestion.",
                    item_type=WorkItemType.INCIDENT,
                    priority=WorkItemPriority.CRITICAL,
                    status=WorkItemStatus.IN_PROGRESS,
                    team_id=team_core.id,
                    assignee_id=member.id,
                    reporter_id=manager.id,
                    due_date=now + timedelta(days=1),
                    version=1,
                ),
                WorkItem(
                    title="Implement automated database snapshot verification",
                    description="Nightly job to spin up temporary PostgreSQL instance and verify integrity of WAL backups.",
                    item_type=WorkItemType.FEATURE,
                    priority=WorkItemPriority.HIGH,
                    status=WorkItemStatus.OPEN,
                    team_id=team_core.id,
                    assignee_id=None,  # Unassigned for concurrent claim testing!
                    reporter_id=admin.id,
                    due_date=now + timedelta(days=7),
                    version=1,
                ),
                WorkItem(
                    title="Rotate IAM service credentials for telemetry pipeline",
                    description="90-day rotation required under SOC2 policy for production log forwarder credentials.",
                    item_type=WorkItemType.TASK,
                    priority=WorkItemPriority.MEDIUM,
                    status=WorkItemStatus.BLOCKED,
                    team_id=team_ops.id,
                    assignee_id=member2.id,
                    reporter_id=manager.id,
                    due_date=now + timedelta(days=3),
                    version=1,
                ),
                WorkItem(
                    title="Upgrade OpenSSL library on edge reverse proxies",
                    description="Security advisory CVE-2026-4412 requires updating OpenSSL on all perimeter gateway nodes.",
                    item_type=WorkItemType.BUG,
                    priority=WorkItemPriority.CRITICAL,
                    status=WorkItemStatus.RESOLVED,
                    team_id=team_ops.id,
                    assignee_id=member2.id,
                    reporter_id=admin.id,
                    due_date=now - timedelta(days=1),
                    version=1,
                ),
                WorkItem(
                    title="Unassigned high-priority SSL certificate renewal",
                    description="Wildcard certificate for internal staging domain expires in 48 hours.",
                    item_type=WorkItemType.TASK,
                    priority=WorkItemPriority.HIGH,
                    status=WorkItemStatus.OPEN,
                    team_id=team_ops.id,
                    assignee_id=None,  # Unassigned for claim testing
                    reporter_id=manager.id,
                    due_date=now + timedelta(days=2),
                    version=1,
                ),
            ]

            for item in samples:
                db.add(item)
                db.flush()
                # Add creation activity log
                log = ActivityLog(
                    work_item_id=item.id,
                    actor_id=item.reporter_id,
                    action="CREATED",
                    new_value=f"Initial item created with status {item.status.value}",
                    timestamp=now,
                )
                db.add(log)

            db.commit()
            print(f"Seeded {len(samples)} initial work items with activity records.")

        print("\nSeed completed successfully!")
        print("=" * 60)
        print("Default accounts created:")
        print(f"  Admin:   {settings.ADMIN_INITIAL_EMAIL} / {settings.ADMIN_INITIAL_PASSWORD}")
        print("  Manager: manager@newtonite.io / ManagerPass123!")
        print("  Member:  member@newtonite.io / MemberPass123!")
        print("  Member2: dev@newtonite.io / DevPass123!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
