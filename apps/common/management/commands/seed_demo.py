"""
Seed command for Workline.
Creates demo workspace, role accounts, projects, milestones, tasks,
dependencies, comments, time entries, and tags.
Safe and idempotent.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.accounts.models import Role, UserProfile
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.projects.models import Project, ProjectStatus, Milestone, MilestoneStatus, ProjectMembership
from apps.tasks.models import Task, TaskStatus, TaskPriority, Tag, TaskDependency, DependencyType, Comment, TimeEntry
from apps.notifications.models import ActivityEvent, ActivityEventType, Notification


class Command(BaseCommand):
    help = 'Seeds realistic demo workspace, users, projects, tasks, and dependencies for Workline.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting Workline demo seeding...'))

        today = timezone.localdate()
        now = timezone.now()

        # 1. Users & Roles
        demo_password = 'WorklineDemo2026!'
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@workline.local',
                'first_name': 'Sarah',
                'last_name': 'Vance',
                'role': Role.ADMIN,
                'job_title': 'VP of Engineering',
                'avatar_color': '#4f46e5',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'manager',
                'email': 'manager@workline.local',
                'first_name': 'Marcus',
                'last_name': 'Brody',
                'role': Role.MANAGER,
                'job_title': 'Engineering Lead & Project Manager',
                'avatar_color': '#0ea5e9',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'username': 'alex',
                'email': 'alex@workline.local',
                'first_name': 'Alex',
                'last_name': 'Rivera',
                'role': Role.MEMBER,
                'job_title': 'Senior Frontend Engineer',
                'avatar_color': '#10b981',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'maya',
                'email': 'maya@workline.local',
                'first_name': 'Maya',
                'last_name': 'Chen',
                'role': Role.MEMBER,
                'job_title': 'Backend Systems Engineer',
                'avatar_color': '#f59e0b',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'taylor',
                'email': 'taylor@workline.local',
                'first_name': 'Taylor',
                'last_name': 'Jordan',
                'role': Role.VIEWER,
                'job_title': 'Product Stakeholder & Auditor',
                'avatar_color': '#8b5cf6',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        created_users = {}
        for ud in users_data:
            user, created = User.objects.get_or_create(
                username=ud['username'],
                defaults={
                    'email': ud['email'],
                    'first_name': ud['first_name'],
                    'last_name': ud['last_name'],
                    'is_staff': ud['is_staff'],
                    'is_superuser': ud['is_superuser'],
                }
            )
            if created:
                user.set_password(demo_password)
                user.save()
                self.stdout.write(f"  Created user: {user.username} ({ud['email']})")
            else:
                self.stdout.write(f"  Existing user: {user.username}")

            # Ensure profile exists and sync attributes
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = ud['role']
            profile.job_title = ud['job_title']
            profile.avatar_color = ud['avatar_color']
            profile.weekly_capacity_hours = 40
            profile.save()
            created_users[ud['username']] = user

        admin_user = created_users['admin']
        manager_user = created_users['manager']
        alex = created_users['alex']
        maya = created_users['maya']
        taylor = created_users['taylor']

        # 2. Workspace
        workspace, ws_created = Workspace.objects.get_or_create(
            name='Acme Product Engineering',
            defaults={
                'slug': 'acme-product-engineering',
                'description': 'Main workspace for core engineering, infrastructure and product development.',
                'timezone': 'UTC',
                'created_by': admin_user,
            }
        )
        if ws_created:
            self.stdout.write(f"  Created workspace: {workspace.name}")
        else:
            self.stdout.write(f"  Existing workspace: {workspace.name}")

        # Memberships
        for user in created_users.values():
            role = user.profile.role
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=user,
                defaults={'role': role}
            )

        # 3. Tags
        tag_definitions = [
            ('Frontend', '#3b82f6'),
            ('Backend', '#10b981'),
            ('DevOps', '#f59e0b'),
            ('Design', '#ec4899'),
            ('Security', '#ef4444'),
            ('High Priority', '#dc2626'),
            ('Documentation', '#6366f1'),
        ]
        created_tags = {}
        for tname, tcolor in tag_definitions:
            tag, _ = Tag.objects.get_or_create(workspace=workspace, name=tname, defaults={'color': tcolor})
            created_tags[tname] = tag

        # 4. Projects
        projects_data = [
            {
                'key': 'MAR',
                'name': 'Mobile App Redesign',
                'description': 'Revamp native mobile applications for iOS & Android with new design system and offline sync.',
                'owner': manager_user,
                'status': ProjectStatus.ACTIVE,
                'color': '#4f46e5',
                'start_date': today - timedelta(days=20),
                'due_date': today + timedelta(days=40),
            },
            {
                'key': 'API',
                'name': 'Core API v2 Migration',
                'description': 'High-performance GraphQL and REST API migration with distributed caching and OAuth2 token auth.',
                'owner': manager_user,
                'status': ProjectStatus.ACTIVE,
                'color': '#059669',
                'start_date': today - timedelta(days=15),
                'due_date': today + timedelta(days=25),
            },
            {
                'key': 'SOC',
                'name': 'Security & SOC2 Compliance',
                'description': 'Audit readiness, role-based access reviews, automated vulnerability scanning, and SIEM integration.',
                'owner': admin_user,
                'status': ProjectStatus.ACTIVE,
                'color': '#d97706',
                'start_date': today - timedelta(days=30),
                'due_date': today + timedelta(days=60),
            },
        ]

        created_projects = {}
        for pdata in projects_data:
            proj, _ = Project.objects.get_or_create(
                workspace=workspace,
                key=pdata['key'],
                defaults=pdata
            )
            created_projects[pdata['key']] = proj
            # Project memberships
            for user in created_users.values():
                role = 'LEAD' if user == proj.owner else ('VIEWER' if user == taylor else 'CONTRIBUTOR')
                ProjectMembership.objects.get_or_create(
                    project=proj,
                    user=user,
                    defaults={'project_role': role}
                )

        mar = created_projects['MAR']
        api = created_projects['API']
        soc = created_projects['SOC']

        # 5. Milestones
        milestones_data = [
            (mar, 'Design System & Token Freeze', today - timedelta(days=5), MilestoneStatus.ACHIEVED),
            (mar, 'Beta TestFlight Release', today + timedelta(days=15), MilestoneStatus.UPCOMING),
            (mar, 'App Store & Play Store Launch', today + timedelta(days=35), MilestoneStatus.UPCOMING),
            (api, 'Database Schema & Query Optimization', today - timedelta(days=2), MilestoneStatus.ACHIEVED),
            (api, 'v2 Endpoints Feature Parity', today + timedelta(days=10), MilestoneStatus.UPCOMING),
            (soc, 'Access Control Audit Complete', today + timedelta(days=12), MilestoneStatus.UPCOMING),
        ]
        for proj, mname, mdate, mstatus in milestones_data:
            Milestone.objects.get_or_create(
                project=proj,
                name=mname,
                defaults={'due_date': mdate, 'status': mstatus}
            )

        # 6. Tasks (At least 28 realistic tasks spanning various statuses, priorities, assignees, dates)
        tasks_data = [
            # MAR tasks
            {
                'project': mar,
                'title': 'Design new navigation patterns and tab bar',
                'description': 'Create interactive Figma prototypes for the refreshed bottom navigation and sheet modals.',
                'status': TaskStatus.DONE,
                'priority': TaskPriority.HIGH,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today - timedelta(days=18),
                'due_date': today - timedelta(days=8),
                'estimate_hours': Decimal('16.0'),
                'progress_percent': 100,
                'tags': ['Design', 'Frontend'],
            },
            {
                'project': mar,
                'title': 'Implement dark mode theme tokens in mobile client',
                'description': 'Integrate Tailwind-inspired theme tokens into React Native style engine.',
                'status': TaskStatus.DONE,
                'priority': TaskPriority.MEDIUM,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today - timedelta(days=10),
                'due_date': today - timedelta(days=3),
                'estimate_hours': Decimal('12.0'),
                'progress_percent': 100,
                'tags': ['Frontend'],
            },
            {
                'project': mar,
                'title': 'Build offline SQLite caching layer for tasks',
                'description': 'Allow users to browse and queue task modifications when device is offline.',
                'status': TaskStatus.IN_PROGRESS,
                'priority': TaskPriority.URGENT,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today - timedelta(days=4),
                'due_date': today + timedelta(days=5),
                'estimate_hours': Decimal('24.0'),
                'progress_percent': 60,
                'tags': ['Frontend', 'High Priority'],
            },
            {
                'project': mar,
                'title': 'Set up biometric FaceID & Fingerprint login flow',
                'description': 'Implement local auth hardware prompt and keychain token recovery.',
                'status': TaskStatus.IN_REVIEW,
                'priority': TaskPriority.HIGH,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today - timedelta(days=6),
                'due_date': today + timedelta(days=2),
                'estimate_hours': Decimal('14.0'),
                'progress_percent': 85,
                'tags': ['Frontend', 'Security'],
            },
            {
                'project': mar,
                'title': 'Resolve push notification crash on Android 14',
                'description': 'Foreground service permission exception occurs when handling silent sync payloads.',
                'status': TaskStatus.BLOCKED,
                'priority': TaskPriority.URGENT,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today - timedelta(days=7),
                'due_date': today - timedelta(days=1), # OVERDUE & BLOCKED!
                'estimate_hours': Decimal('10.0'),
                'progress_percent': 30,
                'blocked_reason': 'Waiting for upstream library bugfix in firebase-messaging-android v23.4.1.',
                'tags': ['Frontend', 'High Priority'],
            },
            {
                'project': mar,
                'title': 'Create onboarding interactive carousel walkthrough',
                'description': 'Guide first-time team members through workspace shortcuts and notification settings.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.MEDIUM,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today + timedelta(days=3),
                'due_date': today + timedelta(days=12),
                'estimate_hours': Decimal('12.0'),
                'progress_percent': 0,
                'tags': ['Frontend', 'Design'],
            },
            {
                'project': mar,
                'title': 'Performance profile list scrolling with 5,000 items',
                'description': 'Run Hermes memory profiler to check for card re-render leaks during fast scroll.',
                'status': TaskStatus.BACKLOG,
                'priority': TaskPriority.LOW,
                'assignee': None, # UNASSIGNED
                'reporter': manager_user,
                'start_date': today + timedelta(days=10),
                'due_date': today + timedelta(days=20),
                'estimate_hours': Decimal('8.0'),
                'progress_percent': 0,
                'tags': ['Frontend'],
            },
            {
                'project': mar,
                'title': 'Implement iPad multi-column split view layout',
                'description': 'Support tablet responsive layout with pinned left navigation and inspector panel.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.LOW,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today + timedelta(days=14),
                'due_date': today + timedelta(days=28),
                'estimate_hours': Decimal('16.0'),
                'progress_percent': 0,
                'tags': ['Frontend', 'Design'],
            },

            # API tasks
            {
                'project': api,
                'title': 'Define v2 OpenAPI specifications and schemas',
                'description': 'Standardize pagination, filtering params, and unified error JSON envelopes.',
                'status': TaskStatus.DONE,
                'priority': TaskPriority.HIGH,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today - timedelta(days=14),
                'due_date': today - timedelta(days=6),
                'estimate_hours': Decimal('16.0'),
                'progress_percent': 100,
                'tags': ['Backend', 'Documentation'],
            },
            {
                'project': api,
                'title': 'Migrate task filter endpoints to composite indexes',
                'description': 'Add compound B-tree index on (project_id, status) and (assignee_id, due_date).',
                'status': TaskStatus.DONE,
                'priority': TaskPriority.MEDIUM,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today - timedelta(days=8),
                'due_date': today - timedelta(days=1),
                'estimate_hours': Decimal('10.0'),
                'progress_percent': 100,
                'tags': ['Backend', 'DevOps'],
            },
            {
                'project': api,
                'title': 'Implement GraphQL DataLoader for Task assignees & tags',
                'description': 'Eliminate N+1 query bottlenecks when querying projects with multiple nested tasks.',
                'status': TaskStatus.IN_PROGRESS,
                'priority': TaskPriority.HIGH,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today - timedelta(days=3),
                'due_date': today + timedelta(days=4),
                'estimate_hours': Decimal('18.0'),
                'progress_percent': 50,
                'tags': ['Backend'],
            },
            {
                'project': api,
                'title': 'Implement rate limiting and token bucket throttles',
                'description': 'Protect public API endpoints with Redis-backed sliding window rate limiter.',
                'status': TaskStatus.IN_REVIEW,
                'priority': TaskPriority.HIGH,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today - timedelta(days=5),
                'due_date': today + timedelta(days=1),
                'estimate_hours': Decimal('12.0'),
                'progress_percent': 90,
                'tags': ['Backend', 'Security'],
            },
            {
                'project': api,
                'title': 'Fix webhook retry timeout under high concurrency',
                'description': 'Deadlock occurs when webhook delivery workers exceed PostgreSQL max pool connections.',
                'status': TaskStatus.BLOCKED,
                'priority': TaskPriority.URGENT,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today - timedelta(days=5),
                'due_date': today - timedelta(days=2), # OVERDUE & BLOCKED!
                'estimate_hours': Decimal('8.0'),
                'progress_percent': 20,
                'blocked_reason': 'Need DevOps approval to increase connection pool and provision PgBouncer.',
                'tags': ['Backend', 'DevOps', 'High Priority'],
            },
            {
                'project': api,
                'title': 'Automate Swagger/Redoc interactive documentation build',
                'description': 'Configure CI action to publish interactive schema explorer on every release tag.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.LOW,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today + timedelta(days=2),
                'due_date': today + timedelta(days=8),
                'estimate_hours': Decimal('6.0'),
                'progress_percent': 0,
                'tags': ['Backend', 'Documentation'],
            },
            {
                'project': api,
                'title': 'Architect webhook signing with HMAC-SHA256 headers',
                'description': 'Ensure destination webhook listeners can cryptographically verify origin authenticity.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.MEDIUM,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today + timedelta(days=6),
                'due_date': today + timedelta(days=15),
                'estimate_hours': Decimal('14.0'),
                'progress_percent': 0,
                'tags': ['Backend', 'Security'],
            },
            {
                'project': api,
                'title': 'Load testing API gateway with Locust to 10k RPS',
                'description': 'Simulate spike traffic and monitor latency percentiles p95 and p99.',
                'status': TaskStatus.BACKLOG,
                'priority': TaskPriority.MEDIUM,
                'assignee': None, # UNASSIGNED
                'reporter': manager_user,
                'start_date': today + timedelta(days=12),
                'due_date': today + timedelta(days=24),
                'estimate_hours': Decimal('20.0'),
                'progress_percent': 0,
                'tags': ['Backend', 'DevOps'],
            },

            # SOC tasks
            {
                'project': soc,
                'title': 'Audit production database access and rotate root credentials',
                'description': 'Review IAM policies, remove unused admin roles, and enforce KMS key rotation.',
                'status': TaskStatus.DONE,
                'priority': TaskPriority.URGENT,
                'assignee': admin_user,
                'reporter': admin_user,
                'start_date': today - timedelta(days=25),
                'due_date': today - timedelta(days=15),
                'estimate_hours': Decimal('12.0'),
                'progress_percent': 100,
                'tags': ['Security', 'DevOps'],
            },
            {
                'project': soc,
                'title': 'Implement automated Dependency-Track vulnerability scanning',
                'description': 'Scan SBOM files on every merge to main and notify Slack security channel.',
                'status': TaskStatus.DONE,
                'priority': TaskPriority.HIGH,
                'assignee': maya,
                'reporter': admin_user,
                'start_date': today - timedelta(days=18),
                'due_date': today - timedelta(days=8),
                'estimate_hours': Decimal('14.0'),
                'progress_percent': 100,
                'tags': ['Security', 'DevOps'],
            },
            {
                'project': soc,
                'title': 'Enforce mandatory multi-factor authentication for all team members',
                'description': 'Configure WebAuthn/TOTP requirement before granting workspace write access.',
                'status': TaskStatus.IN_PROGRESS,
                'priority': TaskPriority.URGENT,
                'assignee': admin_user,
                'reporter': admin_user,
                'start_date': today - timedelta(days=4),
                'due_date': today + timedelta(days=3),
                'estimate_hours': Decimal('16.0'),
                'progress_percent': 70,
                'tags': ['Security', 'High Priority'],
            },
            {
                'project': soc,
                'title': 'Review data retention policies and configure automated backups',
                'description': 'Implement point-in-time recovery testing and verify 30-day cold storage archiving.',
                'status': TaskStatus.IN_REVIEW,
                'priority': TaskPriority.HIGH,
                'assignee': manager_user,
                'reporter': admin_user,
                'start_date': today - timedelta(days=6),
                'due_date': today + timedelta(days=2),
                'estimate_hours': Decimal('10.0'),
                'progress_percent': 85,
                'tags': ['Security', 'DevOps'],
            },
            {
                'project': soc,
                'title': 'Document Disaster Recovery runbook and failover procedure',
                'description': 'Write step-by-step recovery guide for secondary AWS/Azure region standby failover.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.MEDIUM,
                'assignee': manager_user,
                'reporter': admin_user,
                'start_date': today + timedelta(days=1),
                'due_date': today + timedelta(days=9),
                'estimate_hours': Decimal('12.0'),
                'progress_percent': 0,
                'tags': ['Documentation', 'Security'],
            },
            {
                'project': soc,
                'title': 'Vendor third-party SOC2 Type II penetration testing',
                'description': 'Schedule external black-box and white-box pen test engagement for Q4.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.HIGH,
                'assignee': admin_user,
                'reporter': admin_user,
                'start_date': today + timedelta(days=8),
                'due_date': today + timedelta(days=25),
                'estimate_hours': Decimal('8.0'),
                'progress_percent': 0,
                'tags': ['Security'],
            },
            {
                'project': soc,
                'title': 'Establish employee offboarding security revocation checklist',
                'description': 'Ensure immediate automated revoking of GitHub, AWS, GSuite, and VPN certificates.',
                'status': TaskStatus.TODO,
                'priority': TaskPriority.LOW,
                'assignee': None, # UNASSIGNED
                'reporter': admin_user,
                'start_date': today + timedelta(days=10),
                'due_date': today + timedelta(days=20),
                'estimate_hours': Decimal('6.0'),
                'progress_percent': 0,
                'tags': ['Security', 'Documentation'],
            },
            {
                'project': soc,
                'title': 'Conduct quarterly security awareness phishing simulation',
                'description': 'Deploy educational campaign to identify and train team members on modern phishing vectors.',
                'status': TaskStatus.BACKLOG,
                'priority': TaskPriority.LOW,
                'assignee': None, # UNASSIGNED
                'reporter': admin_user,
                'start_date': today + timedelta(days=15),
                'due_date': today + timedelta(days=35),
                'estimate_hours': Decimal('5.0'),
                'progress_percent': 0,
                'tags': ['Security'],
            },

            # Additional Cross-functional Overdue Tasks (so overdue KPI has realistic non-blocked examples too)
            {
                'project': mar,
                'title': 'Refactor user profile avatar upload to support HEIC',
                'description': 'Convert iOS camera roll photos to optimized WebP format on upload.',
                'status': TaskStatus.IN_PROGRESS,
                'priority': TaskPriority.MEDIUM,
                'assignee': alex,
                'reporter': manager_user,
                'start_date': today - timedelta(days=12),
                'due_date': today - timedelta(days=3), # OVERDUE!
                'estimate_hours': Decimal('8.0'),
                'progress_percent': 40,
                'tags': ['Frontend'],
            },
            {
                'project': api,
                'title': 'Fix slow query in task activity audit history serialization',
                'description': 'Activity event query is doing unindexed sorting when filtering by workspace.',
                'status': TaskStatus.IN_PROGRESS,
                'priority': TaskPriority.HIGH,
                'assignee': maya,
                'reporter': manager_user,
                'start_date': today - timedelta(days=7),
                'due_date': today - timedelta(days=1), # OVERDUE!
                'estimate_hours': Decimal('6.0'),
                'progress_percent': 75,
                'tags': ['Backend'],
            },
        ]

        created_tasks = []
        for tdata in tasks_data:
            tag_names = tdata.pop('tags', [])
            task, created = Task.objects.get_or_create(
                project=tdata['project'],
                title=tdata['title'],
                defaults=tdata
            )
            if not created:
                # Update properties if already exists
                for k, v in tdata.items():
                    setattr(task, k, v)
                task.save()

            # Assign tags
            if tag_names:
                task.tags.set([created_tags[tn] for tn in tag_names if tn in created_tags])

            created_tasks.append(task)

        self.stdout.write(f"  Created/verified {len(created_tasks)} main tasks.")

        # 7. Subtasks
        parent_offline_task = Task.objects.filter(title__icontains='Build offline SQLite caching layer').first()
        if parent_offline_task:
            subtask_defs = [
                ('Design local schema for tasks & comments', TaskStatus.DONE, 100, alex),
                ('Implement background conflict resolution queue', TaskStatus.IN_PROGRESS, 50, alex),
                ('Unit test sync rollback when network disconnects', TaskStatus.TODO, 0, alex),
            ]
            for stitle, sstatus, sprog, sassignee in subtask_defs:
                Task.objects.get_or_create(
                    project=parent_offline_task.project,
                    title=stitle,
                    parent_task=parent_offline_task,
                    defaults={
                        'description': f"Subtask of {parent_offline_task.identifier}",
                        'status': sstatus,
                        'priority': TaskPriority.HIGH,
                        'assignee': sassignee,
                        'reporter': manager_user,
                        'start_date': parent_offline_task.start_date,
                        'due_date': parent_offline_task.due_date,
                        'estimate_hours': Decimal('6.0'),
                        'progress_percent': sprog,
                    }
                )

        parent_mfa_task = Task.objects.filter(title__icontains='Enforce mandatory multi-factor authentication').first()
        if parent_mfa_task:
            subtask_defs = [
                ('Draft user communication on 2FA rollout schedule', TaskStatus.DONE, 100, admin_user),
                ('Implement QR code secret generator view', TaskStatus.DONE, 100, admin_user),
                ('Test recovery code generation & fallback login', TaskStatus.IN_PROGRESS, 60, admin_user),
            ]
            for stitle, sstatus, sprog, sassignee in subtask_defs:
                Task.objects.get_or_create(
                    project=parent_mfa_task.project,
                    title=stitle,
                    parent_task=parent_mfa_task,
                    defaults={
                        'description': f"Subtask of {parent_mfa_task.identifier}",
                        'status': sstatus,
                        'priority': TaskPriority.URGENT,
                        'assignee': sassignee,
                        'reporter': admin_user,
                        'start_date': parent_mfa_task.start_date,
                        'due_date': parent_mfa_task.due_date,
                        'estimate_hours': Decimal('5.0'),
                        'progress_percent': sprog,
                    }
                )

        # 8. Dependencies (predecessor -> successor, strictly acyclic)
        t_nav = Task.objects.filter(title__icontains='Design new navigation patterns').first()
        t_offline = Task.objects.filter(title__icontains='Build offline SQLite caching layer').first()
        t_bio = Task.objects.filter(title__icontains='Set up biometric FaceID').first()
        t_onboarding = Task.objects.filter(title__icontains='Create onboarding interactive carousel').first()

        t_spec = Task.objects.filter(title__icontains='Define v2 OpenAPI specifications').first()
        t_index = Task.objects.filter(title__icontains='Migrate task filter endpoints').first()
        t_graphql = Task.objects.filter(title__icontains='Implement GraphQL DataLoader').first()
        t_rate = Task.objects.filter(title__icontains='Implement rate limiting').first()

        dependencies = [
            (t_nav, t_bio, DependencyType.BLOCKS),
            (t_nav, t_offline, DependencyType.RELATES_TO),
            (t_bio, t_onboarding, DependencyType.BLOCKS),
            (t_spec, t_index, DependencyType.BLOCKS),
            (t_spec, t_graphql, DependencyType.BLOCKS),
            (t_graphql, t_rate, DependencyType.BLOCKS),
        ]
        for pred, succ, dtype in dependencies:
            if pred and succ and pred.id != succ.id:
                TaskDependency.objects.get_or_create(
                    predecessor_task=pred,
                    successor_task=succ,
                    defaults={'dependency_type': dtype}
                )

        # 9. Comments & Discussions
        comments_data = [
            (t_bio, manager_user, "Alex, have you verified compatibility with Android Keystore on API level 33?"),
            (t_bio, alex, "Yes! Verified in the Android emulator and on physical Pixel 8. BioPrompt handles fallback gracefully."),
            (t_offline, manager_user, "Great progress on the SQLite caching layer. Make sure we validate write conflicts when syncing back."),
            (t_offline, alex, "Added a vector timestamp to the local payload so server resolution is deterministic."),
            (t_graphql, maya, "Benchmarked DataLoader against our staging dataset: query response dropped from 380ms down to 42ms!"),
            (t_graphql, manager_user, "Superb result Maya. That eliminates our primary blocker for mobile list loading."),
        ]
        for t, author, body in comments_data:
            if t:
                Comment.objects.get_or_create(
                    task=t,
                    author=author,
                    body=body
                )

        # 10. Time Entries
        time_entries = [
            (t_nav, alex, Decimal('8.0'), today - timedelta(days=12), "Wireframing and vector icon preparation"),
            (t_nav, alex, Decimal('8.0'), today - timedelta(days=9), "Interactive Figma prototypes and design review"),
            (t_bio, alex, Decimal('6.5'), today - timedelta(days=4), "Native bridge module integration"),
            (t_bio, alex, Decimal('4.0'), today - timedelta(days=1), "Biometric prompt error state handling"),
            (t_offline, alex, Decimal('7.0'), today - timedelta(days=2), "Local SQLite schema migrations"),
            (t_spec, maya, Decimal('8.0'), today - timedelta(days=10), "OpenAPI v3.1 schema definitions"),
            (t_spec, maya, Decimal('7.5'), today - timedelta(days=7), "Error envelope spec & review with mobile team"),
            (t_index, maya, Decimal('6.0'), today - timedelta(days=3), "PostgreSQL index explain analyze testing"),
            (t_graphql, maya, Decimal('9.0'), today - timedelta(days=1), "Dataloader batch loading pipeline"),
        ]
        for t, user, duration, edate, note in time_entries:
            if t:
                TimeEntry.objects.get_or_create(
                    task=t,
                    user=user,
                    duration_hours=duration,
                    entry_date=edate,
                    defaults={'note': note}
                )

        # 11. Activity Events
        if t_bio:
            ActivityEvent.objects.get_or_create(
                workspace=workspace,
                actor=alex,
                project=mar,
                task=t_bio,
                event_type=ActivityEventType.STATUS_CHANGED,
                summary=f"Alex Rivera moved {t_bio.identifier} to In Review",
                metadata={'old_status': 'IN_PROGRESS', 'new_status': 'IN_REVIEW'}
            )
        if t_offline:
            ActivityEvent.objects.get_or_create(
                workspace=workspace,
                actor=alex,
                project=mar,
                task=t_offline,
                event_type=ActivityEventType.TIME_LOGGED,
                summary=f"Alex Rivera logged 7.0 hours on {t_offline.identifier}",
                metadata={'hours': 7.0}
            )

        # 12. In-App Notifications
        if t_bio:
            Notification.objects.get_or_create(
                recipient=manager_user,
                actor=alex,
                task=t_bio,
                project=mar,
                event_type='REVIEW_REQUESTED',
                title=f"Review requested: {t_bio.identifier}",
                message=f"Alex Rivera submitted '{t_bio.title}' for review.",
                link_url=f"/tasks/{t_bio.id}/"
            )
        if t_offline:
            Notification.objects.get_or_create(
                recipient=alex,
                actor=manager_user,
                task=t_offline,
                project=mar,
                event_type='TASK_ASSIGNED',
                title=f"Assigned to {t_offline.identifier}",
                message=f"Marcus Brody assigned you to '{t_offline.title}'.",
                link_url=f"/tasks/{t_offline.id}/"
            )

        self.stdout.write(self.style.SUCCESS(
            "\nSuccessfully seeded Workline demo data!"
            "\nDemo Accounts created with password 'WorklineDemo2026!':"
            "\n  - Admin:   admin@workline.local   (Sarah Vance - VP of Engineering)"
            "\n  - Manager: manager@workline.local (Marcus Brody - Project Lead)"
            "\n  - Member:  alex@workline.local    (Alex Rivera - Senior Frontend)"
            "\n  - Member:  maya@workline.local    (Maya Chen - Backend Systems)"
            "\n  - Viewer:  taylor@workline.local  (Taylor Jordan - Stakeholder/Auditor)"
        ))
