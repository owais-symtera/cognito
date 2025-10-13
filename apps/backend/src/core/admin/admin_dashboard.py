"""
Story 7.1: Administrative Configuration Interface
Comprehensive admin dashboard with pharmaceutical regulatory compliance
"""

import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger

logger = get_logger(__name__)


class UserRole(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    COMPLIANCE = "compliance"


@dataclass
class UserProfile:
    """User profile with organization hierarchy"""
    id: str
    username: str
    email: str
    full_name: str
    roles: List[UserRole]
    organization_id: str
    organization_name: str
    department: Optional[str]
    is_active: bool
    theme_preference: str  # auto, light, dark
    created_at: datetime
    last_login: Optional[datetime]
    permissions: List[str]


@dataclass
class CategoryConfiguration:
    """Category configuration with templates"""
    id: str
    name: str
    display_name: str
    enabled: bool
    template: str
    parameters: Dict[str, Any]
    source_priority: List[str]
    validation_rules: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    updated_by: str
    version: int


@dataclass
class APIConfiguration:
    """API service configuration"""
    id: str
    service_name: str
    api_key_hash: str
    endpoint: str
    rate_limit: int
    cost_per_call: float
    monthly_quota: int
    used_this_month: int
    is_active: bool
    last_used: Optional[datetime]
    error_rate: float


@dataclass
class ApprovalWorkflow:
    """Configuration change approval workflow"""
    id: str
    request_type: str
    requested_by: str
    requested_at: datetime
    changes: Dict[str, Any]
    status: str  # pending, approved, rejected, expired
    approvers: List[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    comments: Optional[str]
    expires_at: datetime


class AdminDashboardService:
    """Administrative dashboard service with audit compliance"""

    def __init__(self, db_client: DatabaseClient, source_tracker: Optional[SourceTracker] = None):
        self.db_client = db_client
        self.source_tracker = source_tracker or SourceTracker()
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def initialize(self):
        """Initialize admin dashboard service"""
        await self._ensure_tables_exist()
        logger.info("Admin dashboard service initialized")

    async def _ensure_tables_exist(self):
        """Ensure administrative tables exist"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(100) PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(200) NOT NULL,
                organization_id VARCHAR(100) NOT NULL,
                department VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                theme_preference VARCHAR(10) DEFAULT 'auto',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                metadata JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id VARCHAR(100) REFERENCES users(id),
                role VARCHAR(50) NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                granted_by VARCHAR(100),
                PRIMARY KEY (user_id, role)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                parent_id VARCHAR(100) REFERENCES organizations(id),
                type VARCHAR(50) NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS category_configurations (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                template TEXT NOT NULL,
                parameters JSONB NOT NULL,
                source_priority JSONB,
                validation_rules JSONB,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR(100)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS category_config_history (
                id SERIAL PRIMARY KEY,
                category_id VARCHAR(100) REFERENCES category_configurations(id),
                version INTEGER NOT NULL,
                changes JSONB NOT NULL,
                changed_by VARCHAR(100) NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rollback_from INTEGER REFERENCES category_config_history(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS api_configurations (
                id VARCHAR(100) PRIMARY KEY,
                service_name VARCHAR(100) UNIQUE NOT NULL,
                api_key_hash VARCHAR(255) NOT NULL,
                endpoint TEXT NOT NULL,
                rate_limit INTEGER DEFAULT 100,
                cost_per_call DECIMAL(10,4) DEFAULT 0.0,
                monthly_quota INTEGER DEFAULT 10000,
                is_active BOOLEAN DEFAULT TRUE,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS api_usage_metrics (
                api_id VARCHAR(100) REFERENCES api_configurations(id),
                date DATE NOT NULL,
                call_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                total_cost DECIMAL(10,2) DEFAULT 0.0,
                avg_response_time_ms INTEGER,
                PRIMARY KEY (api_id, date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS approval_workflows (
                id VARCHAR(100) PRIMARY KEY,
                request_type VARCHAR(50) NOT NULL,
                requested_by VARCHAR(100) NOT NULL,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                changes JSONB NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                approvers JSONB,
                approved_by VARCHAR(100),
                approved_at TIMESTAMP,
                comments TEXT,
                expires_at TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS configuration_backups (
                id VARCHAR(100) PRIMARY KEY,
                description TEXT,
                backup_data JSONB NOT NULL,
                size_bytes INTEGER,
                created_by VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                restored_count INTEGER DEFAULT 0,
                last_restored_at TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS admin_audit_trail (
                id SERIAL PRIMARY KEY,
                action VARCHAR(100) NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                target_type VARCHAR(50),
                target_id VARCHAR(100),
                details JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_trail_user
            ON admin_audit_trail(user_id, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_api_usage_date
            ON api_usage_metrics(date DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_workflows_status
            ON approval_workflows(status, expires_at)
            """
        ])

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            # Check database connection
            db_status = await self._check_database_health()

            # Check API services
            api_status = await self._check_api_health()

            # Check processing pipeline
            pipeline_status = await self._check_pipeline_health()

            # Calculate overall status
            all_healthy = all([
                db_status['healthy'],
                api_status['healthy'],
                pipeline_status['healthy']
            ])

            return {
                "status": "operational" if all_healthy else "degraded",
                "uptime_percentage": await self._calculate_uptime(),
                "components": {
                    "database": db_status,
                    "apis": api_status,
                    "pipeline": pipeline_status
                },
                "last_check": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow()
            }

    async def get_active_processes_summary(self) -> Dict[str, Any]:
        """Get summary of active processes"""
        query = """
            SELECT
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))) as avg_age_seconds
            FROM processing_requests
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            GROUP BY status
        """

        results = await self.db_client.fetch_all(query)

        summary = {
            "active": 0,
            "queued": 0,
            "failed": 0,
            "completed": 0
        }

        for row in results:
            status = row['status'].lower()
            if status in ['processing', 'active']:
                summary['active'] += row['count']
            elif status in ['pending', 'queued']:
                summary['queued'] += row['count']
            elif status == 'failed':
                summary['failed'] = row['count']
            elif status == 'completed':
                summary['completed'] = row['count']

        return summary

    async def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent system activity"""
        query = """
            SELECT
                r.request_id,
                r.category,
                r.status,
                r.created_at,
                r.updated_at,
                u.username as created_by
            FROM processing_requests r
            LEFT JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
            LIMIT %s
        """

        results = await self.db_client.fetch_all(query, (limit,))

        activities = []
        for row in results:
            activities.append({
                "request_id": row['request_id'],
                "category": row['category'],
                "status": row['status'],
                "created_at": row['created_at'].isoformat(),
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                "created_by": row['created_by'] or "system"
            })

        return activities

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        query = """
            SELECT
                COUNT(*) as total_requests,
                AVG(CASE WHEN status = 'completed'
                    THEN EXTRACT(EPOCH FROM (updated_at - created_at))
                    END) as avg_processing_time,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 /
                    NULLIF(COUNT(*), 0) as success_rate
            FROM processing_requests
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """

        result = await self.db_client.fetch_one(query)

        return {
            "total_requests_24h": result['total_requests'] or 0,
            "avg_processing_time_seconds": result['avg_processing_time'] or 0,
            "success_rate": result['success_rate'] or 0,
            "timestamp": datetime.utcnow()
        }

    async def get_categories(self, enabled_only: bool = False) -> List[CategoryConfiguration]:
        """Get category configurations"""
        query = """
            SELECT * FROM category_configurations
            WHERE 1=1
        """
        params = []

        if enabled_only:
            query += " AND enabled = TRUE"

        query += " ORDER BY name"

        results = await self.db_client.fetch_all(query, tuple(params))

        categories = []
        for row in results:
            categories.append(CategoryConfiguration(
                id=row['id'],
                name=row['name'],
                display_name=row['display_name'],
                enabled=row['enabled'],
                template=row['template'],
                parameters=json.loads(row['parameters']),
                source_priority=json.loads(row['source_priority']) if row['source_priority'] else [],
                validation_rules=json.loads(row['validation_rules']) if row['validation_rules'] else {},
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                updated_by=row['updated_by'],
                version=row['version']
            ))

        return categories

    async def get_category(self, category_id: str) -> Optional[CategoryConfiguration]:
        """Get specific category configuration"""
        query = """
            SELECT * FROM category_configurations
            WHERE id = %s OR name = %s
        """

        result = await self.db_client.fetch_one(query, (category_id, category_id))

        if result:
            return CategoryConfiguration(
                id=result['id'],
                name=result['name'],
                display_name=result['display_name'],
                enabled=result['enabled'],
                template=result['template'],
                parameters=json.loads(result['parameters']),
                source_priority=json.loads(result['source_priority']) if result['source_priority'] else [],
                validation_rules=json.loads(result['validation_rules']) if result['validation_rules'] else {},
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                updated_by=result['updated_by'],
                version=result['version']
            )

        return None

    async def update_category_configuration(self,
                                           category_id: str,
                                           updates: Dict[str, Any],
                                           user_id: str) -> CategoryConfiguration:
        """Update category configuration"""
        # Record current version in history
        current = await self.get_category(category_id)
        if current:
            history_query = """
                INSERT INTO category_config_history
                (category_id, version, changes, changed_by)
                VALUES (%s, %s, %s, %s)
            """
            await self.db_client.execute(
                history_query,
                (category_id, current.version, json.dumps(updates), user_id)
            )

        # Update configuration
        update_fields = []
        params = []

        if 'enabled' in updates:
            update_fields.append("enabled = %s")
            params.append(updates['enabled'])

        if 'template' in updates:
            update_fields.append("template = %s")
            params.append(updates['template'])

        if 'parameters' in updates:
            update_fields.append("parameters = %s")
            params.append(json.dumps(updates['parameters']))

        if 'source_priority' in updates:
            update_fields.append("source_priority = %s")
            params.append(json.dumps(updates['source_priority']))

        if 'validation_rules' in updates:
            update_fields.append("validation_rules = %s")
            params.append(json.dumps(updates['validation_rules']))

        update_fields.extend([
            "updated_at = CURRENT_TIMESTAMP",
            "updated_by = %s",
            "version = version + 1"
        ])
        params.extend([user_id, category_id])

        query = f"""
            UPDATE category_configurations
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """

        result = await self.db_client.fetch_one(query, tuple(params))

        # Log audit trail
        await self.log_audit_trail(
            action="category_config_updated",
            user_id=user_id,
            details={
                "category_id": category_id,
                "changes": updates
            }
        )

        return await self.get_category(category_id)

    async def get_users(self,
                       organization_id: Optional[str] = None,
                       role: Optional[str] = None) -> List[UserProfile]:
        """Get users with optional filters"""
        query = """
            SELECT
                u.*,
                o.name as organization_name,
                array_agg(ur.role) as roles
            FROM users u
            LEFT JOIN organizations o ON u.organization_id = o.id
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            WHERE 1=1
        """
        params = []

        if organization_id:
            query += " AND u.organization_id = %s"
            params.append(organization_id)

        if role:
            query += " AND ur.role = %s"
            params.append(role)

        query += " GROUP BY u.id, o.name ORDER BY u.username"

        results = await self.db_client.fetch_all(query, tuple(params))

        users = []
        for row in results:
            users.append(UserProfile(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                full_name=row['full_name'],
                roles=[UserRole(r) for r in (row['roles'] or [])],
                organization_id=row['organization_id'],
                organization_name=row['organization_name'] or "",
                department=row['department'],
                is_active=row['is_active'],
                theme_preference=row['theme_preference'],
                created_at=row['created_at'],
                last_login=row['last_login'],
                permissions=self._get_role_permissions(row['roles'] or [])
            ))

        return users

    async def create_user(self, user_data: Dict[str, Any]) -> UserProfile:
        """Create new user"""
        import uuid

        user_id = str(uuid.uuid4())

        # Hash password
        password_hash = hashlib.sha256(
            user_data['password'].encode()
        ).hexdigest()

        # Insert user
        query = """
            INSERT INTO users
            (id, username, email, password_hash, full_name,
             organization_id, department, theme_preference)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                user_id,
                user_data['username'],
                user_data['email'],
                password_hash,
                user_data['full_name'],
                user_data['organization_id'],
                user_data.get('department'),
                user_data.get('theme_preference', 'auto')
            )
        )

        # Add roles
        for role in user_data.get('roles', []):
            role_query = """
                INSERT INTO user_roles (user_id, role, granted_by)
                VALUES (%s, %s, %s)
            """
            await self.db_client.execute(
                role_query,
                (user_id, role, user_data.get('created_by', 'system'))
            )

        return await self.get_user(user_id)

    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get specific user"""
        users = await self.get_users()
        return next((u for u in users if u.id == user_id), None)

    async def get_api_configurations(self) -> List[APIConfiguration]:
        """Get API configurations with usage stats"""
        query = """
            SELECT
                a.*,
                COALESCE(SUM(u.call_count), 0) as used_this_month,
                COALESCE(AVG(u.error_count::float / NULLIF(u.call_count, 0)), 0) as error_rate
            FROM api_configurations a
            LEFT JOIN api_usage_metrics u ON a.id = u.api_id
                AND u.date >= DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY a.id
            ORDER BY a.service_name
        """

        results = await self.db_client.fetch_all(query)

        apis = []
        for row in results:
            apis.append(APIConfiguration(
                id=row['id'],
                service_name=row['service_name'],
                api_key_hash=row['api_key_hash'],
                endpoint=row['endpoint'],
                rate_limit=row['rate_limit'],
                cost_per_call=float(row['cost_per_call']),
                monthly_quota=row['monthly_quota'],
                used_this_month=int(row['used_this_month']),
                is_active=row['is_active'],
                last_used=None,  # Would need separate query
                error_rate=float(row['error_rate'] or 0)
            ))

        return apis

    async def update_api_configuration(self,
                                      api_id: str,
                                      updates: Dict[str, Any]) -> APIConfiguration:
        """Update API configuration"""
        update_fields = []
        params = []

        if 'endpoint' in updates:
            update_fields.append("endpoint = %s")
            params.append(updates['endpoint'])

        if 'rate_limit' in updates:
            update_fields.append("rate_limit = %s")
            params.append(updates['rate_limit'])

        if 'monthly_quota' in updates:
            update_fields.append("monthly_quota = %s")
            params.append(updates['monthly_quota'])

        if 'is_active' in updates:
            update_fields.append("is_active = %s")
            params.append(updates['is_active'])

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(api_id)

        query = f"""
            UPDATE api_configurations
            SET {', '.join(update_fields)}
            WHERE id = %s
        """

        await self.db_client.execute(query, tuple(params))

        # Get updated configuration
        apis = await self.get_api_configurations()
        return next((a for a in apis if a.id == api_id), None)

    async def create_backup(self, description: str, user_id: str) -> Dict[str, Any]:
        """Create configuration backup"""
        import uuid

        backup_id = str(uuid.uuid4())

        # Gather all configuration data
        backup_data = {
            "categories": [c.__dict__ for c in await self.get_categories()],
            "apis": [a.__dict__ for a in await self.get_api_configurations()],
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }

        # Calculate size
        backup_json = json.dumps(backup_data)
        size_bytes = len(backup_json.encode())

        # Store backup
        query = """
            INSERT INTO configuration_backups
            (id, description, backup_data, size_bytes, created_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
        """

        result = await self.db_client.fetch_one(
            query,
            (backup_id, description, backup_json, size_bytes, user_id)
        )

        # Audit trail
        await self.log_audit_trail(
            action="configuration_backup_created",
            user_id=user_id,
            details={"backup_id": backup_id}
        )

        return {
            "id": result['id'],
            "created_at": result['created_at'],
            "size_bytes": size_bytes
        }

    async def restore_configuration(self, backup_id: str, user_id: str):
        """Restore configuration from backup"""
        # Get backup
        query = """
            SELECT backup_data
            FROM configuration_backups
            WHERE id = %s
        """
        result = await self.db_client.fetch_one(query, (backup_id,))

        if not result:
            raise ValueError(f"Backup {backup_id} not found")

        backup_data = json.loads(result['backup_data'])

        # Restore categories
        for category in backup_data.get('categories', []):
            await self.update_category_configuration(
                category['id'],
                category,
                user_id
            )

        # Restore APIs
        for api in backup_data.get('apis', []):
            await self.update_api_configuration(
                api['id'],
                api
            )

        # Update backup usage
        update_query = """
            UPDATE configuration_backups
            SET restored_count = restored_count + 1,
                last_restored_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        await self.db_client.execute(update_query, (backup_id,))

        # Audit trail
        await self.log_audit_trail(
            action="configuration_restored",
            user_id=user_id,
            details={"backup_id": backup_id}
        )

    async def create_approval_workflow(self,
                                      request_type: str,
                                      requested_by: str,
                                      changes: Dict[str, Any]) -> ApprovalWorkflow:
        """Create approval workflow for configuration changes"""
        import uuid

        workflow_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)

        # Determine approvers based on request type
        approvers = await self._get_approvers_for_request(request_type)

        query = """
            INSERT INTO approval_workflows
            (id, request_type, requested_by, changes, approvers, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """

        result = await self.db_client.fetch_one(
            query,
            (
                workflow_id,
                request_type,
                requested_by,
                json.dumps(changes),
                json.dumps(approvers),
                expires_at
            )
        )

        return ApprovalWorkflow(
            id=result['id'],
            request_type=result['request_type'],
            requested_by=result['requested_by'],
            requested_at=result['requested_at'],
            changes=json.loads(result['changes']),
            status=result['status'],
            approvers=json.loads(result['approvers']),
            approved_by=result['approved_by'],
            approved_at=result['approved_at'],
            comments=result['comments'],
            expires_at=result['expires_at']
        )

    async def get_workflows(self, status: Optional[str] = None) -> List[ApprovalWorkflow]:
        """Get approval workflows"""
        query = """
            SELECT * FROM approval_workflows
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY requested_at DESC"

        results = await self.db_client.fetch_all(query, tuple(params))

        workflows = []
        for row in results:
            workflows.append(ApprovalWorkflow(
                id=row['id'],
                request_type=row['request_type'],
                requested_by=row['requested_by'],
                requested_at=row['requested_at'],
                changes=json.loads(row['changes']),
                status=row['status'],
                approvers=json.loads(row['approvers']) if row['approvers'] else [],
                approved_by=row['approved_by'],
                approved_at=row['approved_at'],
                comments=row['comments'],
                expires_at=row['expires_at']
            ))

        return workflows

    async def approve_workflow(self,
                              workflow_id: str,
                              approver_id: str,
                              comments: Optional[str] = None) -> Dict[str, Any]:
        """Approve workflow and apply changes"""
        # Get workflow
        workflows = await self.get_workflows()
        workflow = next((w for w in workflows if w.id == workflow_id), None)

        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow.status != "pending":
            raise ValueError(f"Workflow {workflow_id} is not pending")

        # Check if approver is authorized
        if approver_id not in workflow.approvers:
            raise ValueError(f"User {approver_id} is not authorized to approve this workflow")

        # Update workflow status
        query = """
            UPDATE approval_workflows
            SET status = 'approved',
                approved_by = %s,
                approved_at = CURRENT_TIMESTAMP,
                comments = %s
            WHERE id = %s
        """

        await self.db_client.execute(
            query,
            (approver_id, comments, workflow_id)
        )

        # Apply changes based on request type
        if workflow.request_type == "category_update":
            await self.update_category_configuration(
                workflow.changes['category_id'],
                workflow.changes['updates'],
                approver_id
            )
        elif workflow.request_type == "configuration_restore":
            await self.restore_configuration(
                workflow.changes['backup_id'],
                approver_id
            )

        # Audit trail
        await self.log_audit_trail(
            action="workflow_approved",
            user_id=approver_id,
            details={"workflow_id": workflow_id}
        )

        return {
            "status": "approved",
            "message": "Changes applied successfully"
        }

    async def log_audit_trail(self,
                             action: str,
                             user_id: str,
                             details: Optional[Dict[str, Any]] = None):
        """Log audit trail entry"""
        query = """
            INSERT INTO admin_audit_trail
            (action, user_id, details)
            VALUES (%s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (action, user_id, json.dumps(details) if details else None)
        )

    async def get_audit_trail(self,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             user_id: Optional[str] = None,
                             action: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail records"""
        query = """
            SELECT
                a.*,
                u.username
            FROM admin_audit_trail a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND a.created_at >= %s"
            params.append(start_date)

        if end_date:
            query += " AND a.created_at <= %s"
            params.append(end_date)

        if user_id:
            query += " AND a.user_id = %s"
            params.append(user_id)

        if action:
            query += " AND a.action = %s"
            params.append(action)

        query += " ORDER BY a.created_at DESC LIMIT %s"
        params.append(limit)

        results = await self.db_client.fetch_all(query, tuple(params))

        records = []
        for row in results:
            records.append({
                "id": row['id'],
                "action": row['action'],
                "user_id": row['user_id'],
                "username": row['username'],
                "details": json.loads(row['details']) if row['details'] else None,
                "created_at": row['created_at'].isoformat()
            })

        return records

    async def update_user_preference(self, user_id: str, preferences: Dict[str, Any]):
        """Update user preferences including theme"""
        update_fields = []
        params = []

        if 'theme' in preferences:
            update_fields.append("theme_preference = %s")
            params.append(preferences['theme'])

        if 'metadata' in preferences:
            update_fields.append("metadata = %s")
            params.append(json.dumps(preferences['metadata']))

        params.append(user_id)

        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = %s
        """

        await self.db_client.execute(query, tuple(params))

    # Helper methods

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            query = "SELECT 1"
            await self.db_client.fetch_one(query)
            return {"healthy": True, "status": "connected"}
        except Exception as e:
            return {"healthy": False, "status": "error", "error": str(e)}

    async def _check_api_health(self) -> Dict[str, Any]:
        """Check API services health"""
        apis = await self.get_api_configurations()
        active_apis = [a for a in apis if a.is_active]

        healthy_count = sum(1 for a in active_apis if a.error_rate < 0.05)

        return {
            "healthy": healthy_count == len(active_apis),
            "status": f"{healthy_count}/{len(active_apis)} healthy",
            "details": {
                "total": len(apis),
                "active": len(active_apis),
                "healthy": healthy_count
            }
        }

    async def _check_pipeline_health(self) -> Dict[str, Any]:
        """Check processing pipeline health"""
        summary = await self.get_active_processes_summary()

        return {
            "healthy": summary['failed'] < summary['active'] * 0.1,
            "status": "operational" if summary['active'] > 0 else "idle",
            "details": summary
        }

    async def _calculate_uptime(self) -> float:
        """Calculate system uptime percentage"""
        # Simplified calculation - would need proper downtime tracking
        return 99.9

    def _get_role_permissions(self, roles: List[str]) -> List[str]:
        """Get permissions for roles"""
        permissions = set()

        role_permissions = {
            "admin": ["all"],
            "manager": ["read", "write", "approve"],
            "analyst": ["read", "write"],
            "viewer": ["read"],
            "compliance": ["read", "audit"]
        }

        for role in roles:
            permissions.update(role_permissions.get(role, []))

        return list(permissions)

    async def _get_approvers_for_request(self, request_type: str) -> List[str]:
        """Get list of approvers for request type"""
        # Get users with appropriate roles
        if request_type in ["configuration_restore", "scoring_rollback"]:
            # High risk - require admin
            users = await self.get_users(role="admin")
        else:
            # Normal changes - admin or manager
            admins = await self.get_users(role="admin")
            managers = await self.get_users(role="manager")
            users = admins + managers

        return [u.id for u in users]