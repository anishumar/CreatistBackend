from __future__ import annotations
import uuid
import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
import asyncpg
from fastapi import HTTPException
from src.models.visionboard import (
    VisionBoard, VisionBoardCreate, VisionBoardUpdate, VisionBoardWithGenres,
    Genre, GenreCreate, GenreUpdate, GenreWithAssignments,
    Equipment, EquipmentCreate, EquipmentUpdate,
    GenreAssignment, GenreAssignmentCreate, GenreAssignmentUpdate, GenreAssignmentWithDetails,
    RequiredEquipment, RequiredEquipmentCreate, RequiredEquipmentUpdate,
    VisionBoardTask, VisionBoardTaskCreate, VisionBoardTaskUpdate, VisionBoardTaskWithDetails,
    TaskDependency, TaskDependencyCreate,
    TaskComment, TaskCommentCreate, TaskCommentUpdate,
    TaskAttachment, TaskAttachmentCreate,
    VisionBoardSummary, VisionBoardStats,
    VisionBoardStatus, AssignmentStatus, TaskStatus, EquipmentStatus,
    Invitation, InvitationCreate, InvitationUpdate, InvitationStatus,
    GroupMessage, Draft, DraftComment
)
from src.models.user import User
import json


class VisionBoardHandler:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    def _check_pool(self):
        """Check if database pool is available"""
        if not self.pool:
            raise HTTPException(status_code=503, detail="Database connection not available")

    # Vision Board CRUD Operations
    async def create_notification(self, *, receiver_id, sender_id, object_type, object_id, event_type, data=None, message=None):
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO notifications (receiver_id, sender_id, object_type, object_id, event_type, status, data, message)
                VALUES ($1, $2, $3, $4, $5, 'unread', $6, $7)
            """
            # Serialize data if it's a dict
            if isinstance(data, dict):
                data = json.dumps(data)
            await conn.execute(query, receiver_id, sender_id, object_type, object_id, event_type, data, message)

    async def create_visionboard(self, visionboard: VisionBoardCreate, created_by: uuid.UUID) -> VisionBoard:
        """Create a new vision board and send notification to the creator"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO visionboards (name, description, start_date, end_date, status, created_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, description, start_date, end_date, status, created_at, updated_at, created_by
            """
            row = await conn.fetchrow(
                query,
                visionboard.name,
                visionboard.description,
                visionboard.start_date,
                visionboard.end_date,
                visionboard.status.value,
                created_by
            )
            vb = VisionBoard(**dict(row))

            # Send notification to the creator (generic model)
            await self.create_notification(
                receiver_id=created_by,
                sender_id=created_by,
                object_type="visionboard",
                object_id=vb.id,
                event_type="created",
                data=None,
                message="Your vision board has been created."
            )

            return vb

    async def get_visionboard(self, visionboard_id: uuid.UUID) -> Optional[VisionBoard]:
        """Get a vision board by ID"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, name, description, start_date, end_date, status, created_at, updated_at, created_by
                FROM visionboards WHERE id = $1
            """
            row = await conn.fetchrow(query, visionboard_id)
            return VisionBoard(**dict(row)) if row else None

    async def get_visionboard_with_genres(self, visionboard_id: uuid.UUID) -> Optional[VisionBoardWithGenres]:
        """Get a vision board with all its genres"""
        async with self.pool.acquire() as conn:
            # Get vision board
            vb_query = """
                SELECT id, name, description, start_date, end_date, status, created_at, updated_at, created_by
                FROM visionboards WHERE id = $1
            """
            vb_row = await conn.fetchrow(vb_query, visionboard_id)
            if not vb_row:
                return None

            # Get genres
            genres_query = """
                SELECT id, visionboard_id, name, description, min_required_people, max_allowed_people, created_at
                FROM genres WHERE visionboard_id = $1
            """
            genres_rows = await conn.fetch(genres_query, visionboard_id)
            
            visionboard = VisionBoard(**dict(vb_row))
            genres = [Genre(**dict(row)) for row in genres_rows]
            
            return VisionBoardWithGenres(**visionboard.model_dump(), genres=genres)

    async def update_visionboard(self, visionboard_id: uuid.UUID, updates: VisionBoardUpdate) -> Optional[VisionBoard]:
        """Update a vision board. If status is set to 'Active' or 'Started', notify all partners."""
        async with self.pool.acquire() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            status_being_set = None
            if updates.name is not None:
                set_clauses.append(f"name = ${param_count}")
                values.append(updates.name)
                param_count += 1
            if updates.description is not None:
                set_clauses.append(f"description = ${param_count}")
                values.append(updates.description)
                param_count += 1
            if updates.start_date is not None:
                set_clauses.append(f"start_date = ${param_count}")
                values.append(updates.start_date)
                param_count += 1
            if updates.end_date is not None:
                set_clauses.append(f"end_date = ${param_count}")
                values.append(updates.end_date)
                param_count += 1
            if updates.status is not None:
                set_clauses.append(f"status = ${param_count}")
                values.append(updates.status.value)
                status_being_set = updates.status.value
                param_count += 1
            if not set_clauses:
                return await self.get_visionboard(visionboard_id)
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.datetime.utcnow())
            param_count += 1
            values.append(visionboard_id)
            query = f"""
                UPDATE visionboards 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING id, name, description, start_date, end_date, status, created_at, updated_at, created_by
            """
            row = await conn.fetchrow(query, *values)
            vb = VisionBoard(**dict(row)) if row else None

            # If status is set to 'Active' or 'Started', notify all partners
            if status_being_set and status_being_set.lower() in ["active", "started"]:
                # Get all assigned users (partners) with accepted assignments
                partners_query = """
                    SELECT ga.user_id FROM genre_assignments ga
                    JOIN genres g ON ga.genre_id = g.id
                    WHERE g.visionboard_id = $1 AND ga.status = 'Accepted'
                """
                partner_rows = await conn.fetch(partners_query, visionboard_id)
                partner_ids = [row['user_id'] for row in partner_rows]
                for partner_id in partner_ids:
                    await self.create_notification(
                        receiver_id=partner_id,
                        sender_id=vb.created_by,
                        object_type="visionboard",
                        object_id=vb.id,
                        event_type="started",
                        data=None,
                        message="The vision board has been started."
                    )

            return vb

    async def delete_visionboard(self, visionboard_id: uuid.UUID) -> bool:
        """Delete a vision board (cascade will handle related data)"""
        async with self.pool.acquire() as conn:
            query = "DELETE FROM visionboards WHERE id = $1"
            result = await conn.execute(query, visionboard_id)
            return result == "DELETE 1"

    async def get_user_visionboards(self, *, user_id: uuid.UUID, status: Optional[VisionBoardStatus] = None) -> List[VisionBoard]:
        """Get all vision boards created by a user"""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM visionboards WHERE created_by = $1"
            params = [user_id]
            
            if status:
                query += " AND status = $2"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC"
            
            rows = await conn.fetch(query, *params)
            return [VisionBoard(**dict(row)) for row in rows]

    async def get_user_assigned_visionboards(self, *, user_id: uuid.UUID, status: Optional[VisionBoardStatus] = None) -> List[VisionBoard]:
        """Get all vision boards where a user is assigned/partner and assignment is accepted"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT DISTINCT vb.* 
                FROM visionboards vb
                JOIN genres g ON vb.id = g.visionboard_id
                JOIN genre_assignments ga ON g.id = ga.genre_id
                WHERE ga.user_id = $1 AND ga.status = 'Accepted'
            """
            params = [user_id]
            if status:
                query += " AND vb.status = $2"
                params.append(status.value)
            query += " ORDER BY vb.created_at DESC"
            rows = await conn.fetch(query, *params)
            return [VisionBoard(**dict(row)) for row in rows]

    # Genre Operations
    async def create_genre(self, visionboard_id: uuid.UUID, genre: GenreCreate) -> Genre:
        """Create a new genre for a vision board"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO genres (visionboard_id, name, description, min_required_people, max_allowed_people)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, visionboard_id, name, description, min_required_people, max_allowed_people, created_at
            """
            row = await conn.fetchrow(
                query,
                visionboard_id,
                genre.name,
                genre.description,
                genre.min_required_people,
                genre.max_allowed_people
            )
            return Genre(**dict(row))

    async def get_genre_with_assignments(self, genre_id: uuid.UUID) -> Optional[GenreWithAssignments]:
        """Get a genre with all its assignments"""
        async with self.pool.acquire() as conn:
            # Get genre
            genre_query = """
                SELECT id, visionboard_id, name, description, min_required_people, max_allowed_people, created_at
                FROM genres WHERE id = $1
            """
            genre_row = await conn.fetchrow(genre_query, genre_id)
            if not genre_row:
                return None

            # Get assignments
            assignments_query = """
                SELECT id, genre_id, user_id, status, work_type, payment_type, payment_amount, currency,
                       invited_at, responded_at, assigned_by
                FROM genre_assignments WHERE genre_id = $1
            """
            assignments_rows = await conn.fetch(assignments_query, genre_id)
            
            genre = Genre(**dict(genre_row))
            assignments = [GenreAssignment(**dict(row)) for row in assignments_rows]
            
            return GenreWithAssignments(**genre.model_dump(), assignments=assignments)

    # Equipment Operations
    async def create_equipment(self, equipment: EquipmentCreate) -> Equipment:
        """Create new equipment"""
        async with self.pool.acquire() as conn:
            # Serialize specifications as JSON string if it's a dict
            specs = equipment.specifications
            if isinstance(specs, dict):
                specs = json.dumps(specs)
            query = """
                INSERT INTO equipment (name, description, category, brand, model, specifications)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, description, category, brand, model, specifications
            """
            row = await conn.fetchrow(
                query,
                equipment.name,
                equipment.description,
                equipment.category,
                equipment.brand,
                equipment.model,
                specs
            )
            # Parse specifications back to dict if it's a string
            equipment_data = dict(row)
            if isinstance(equipment_data.get('specifications'), str):
                try:
                    equipment_data['specifications'] = json.loads(equipment_data['specifications'])
                except Exception:
                    pass
            return Equipment(**equipment_data)

    async def get_equipment_by_category(self, category: str) -> List[Equipment]:
        """Get equipment by category"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, name, description, category, brand, model, specifications
                FROM equipment WHERE category = $1
                ORDER BY name
            """
            rows = await conn.fetch(query, category)
            equipment_list = []
            for row in rows:
                equipment_data = dict(row)
                if isinstance(equipment_data.get('specifications'), str):
                    try:
                        equipment_data['specifications'] = json.loads(equipment_data['specifications'])
                    except Exception:
                        pass
                equipment_list.append(Equipment(**equipment_data))
            return equipment_list

    # Genre Assignment Operations
    async def create_genre_assignment(self, assignment: GenreAssignmentCreate, assigned_by: uuid.UUID) -> GenreAssignment:
        """Create a new genre assignment, then create an invitation and notification for the user"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO genre_assignments (genre_id, user_id, status, work_type, payment_type, payment_amount, currency, assigned_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, genre_id, user_id, status, work_type, payment_type, payment_amount, currency, invited_at, responded_at, assigned_by
            """
            from src.models.visionboard import AssignmentStatus
            row = await conn.fetchrow(
                query,
                assignment.genre_id,
                assignment.user_id,
                AssignmentStatus.PENDING.value,
                assignment.work_type.value,
                assignment.payment_type.value,
                assignment.payment_amount,
                assignment.currency,
                assigned_by
            )
            ga = GenreAssignment(**dict(row))

            # Create invitation for the user
            from src.models.visionboard import InvitationCreate
            invitation = InvitationCreate(
                receiver_id=assignment.user_id,
                object_type="genre",
                object_id=assignment.genre_id,
                data={
                    "work_type": assignment.work_type.value,
                    "payment_type": assignment.payment_type.value,
                    "payment_amount": str(assignment.payment_amount) if assignment.payment_amount else None,
                    "currency": assignment.currency
                }
            )
            await self.create_invitation(sender_id=assigned_by, invitation=invitation)

            # Send notification to the user
            await self.create_notification(
                receiver_id=assignment.user_id,
                sender_id=assigned_by,
                object_type="genre",
                object_id=assignment.genre_id,
                event_type="invited",
                data={
                    "work_type": assignment.work_type.value,
                    "payment_type": assignment.payment_type.value,
                    "payment_amount": str(assignment.payment_amount) if assignment.payment_amount else None,
                    "currency": assignment.currency
                },
                message=f"You have been invited to a genre."
            )

            return ga

    async def update_assignment_status(self, assignment_id: uuid.UUID, status: AssignmentStatus, user_id: uuid.UUID) -> Optional[GenreAssignment]:
        """Update assignment status (for accepting/rejecting invitations)"""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE genre_assignments 
                SET status = $1, responded_at = $2
                WHERE id = $3 AND user_id = $4
                RETURNING id, genre_id, user_id, status, work_type, payment_type, payment_amount, currency,
                       invited_at, responded_at, assigned_by
            """
            row = await conn.fetchrow(
                query,
                status.value,
                datetime.datetime.utcnow(),
                assignment_id,
                user_id
            )
            return GenreAssignment(**dict(row)) if row else None

    async def get_user_assignments(self, user_id: uuid.UUID, status: Optional[AssignmentStatus] = None) -> List[GenreAssignmentWithDetails]:
        """Get all assignments for a user with details"""
        async with self.pool.acquire() as conn:
            if status:
                query = """
                    SELECT ga.id, ga.genre_id, ga.user_id, ga.status, ga.work_type, ga.payment_type, 
                           ga.payment_amount, ga.currency, ga.invited_at, ga.responded_at, ga.assigned_by,
                           g.name as genre_name, u.name as user_name
                    FROM genre_assignments ga
                    JOIN genres g ON ga.genre_id = g.id
                    JOIN users u ON ga.user_id = u.id
                    WHERE ga.user_id = $1 AND ga.status = $2
                    ORDER BY ga.invited_at DESC
                """
                rows = await conn.fetch(query, user_id, status.value)
            else:
                query = """
                    SELECT ga.id, ga.genre_id, ga.user_id, ga.status, ga.work_type, ga.payment_type, 
                           ga.payment_amount, ga.currency, ga.invited_at, ga.responded_at, ga.assigned_by,
                           g.name as genre_name, u.name as user_name
                    FROM genre_assignments ga
                    JOIN genres g ON ga.genre_id = g.id
                    JOIN users u ON ga.user_id = u.id
                    WHERE ga.user_id = $1
                    ORDER BY ga.invited_at DESC
                """
                rows = await conn.fetch(query, user_id)
            
            assignments = []
            for row in rows:
                assignment_data = dict(row)
                genre_name = assignment_data.pop('genre_name')
                user_name = assignment_data.pop('user_name')
                
                assignment = GenreAssignment(**assignment_data)
                assignment_with_details = GenreAssignmentWithDetails(
                    **assignment.model_dump(),
                    genre_name=genre_name,
                    user_name=user_name,
                    equipment=[],  # Will be populated separately if needed
                    tasks=[]       # Will be populated separately if needed
                )
                assignments.append(assignment_with_details)
            
            return assignments

    # Task Operations
    async def create_task(self, task: VisionBoardTaskCreate, created_by: uuid.UUID) -> VisionBoardTask:
        """Create a new task"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO tasks (genre_assignment_id, title, description, priority, due_date, estimated_hours, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, genre_assignment_id, title, description, priority, status, due_date, 
                       estimated_hours, actual_hours, created_at, updated_at, created_by
            """
            row = await conn.fetchrow(
                query,
                task.genre_assignment_id,
                task.title,
                task.description,
                task.priority.value,
                task.due_date,
                task.estimated_hours,
                created_by
            )
            return VisionBoardTask(**dict(row))

    async def update_task_status(self, task_id: uuid.UUID, status: TaskStatus, user_id: uuid.UUID) -> Optional[VisionBoardTask]:
        """Update task status"""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE tasks 
                SET status = $1, updated_at = $2
                WHERE id = $3 AND created_by = $4
                RETURNING id, genre_assignment_id, title, description, priority, status, due_date, 
                       estimated_hours, actual_hours, created_at, updated_at, created_by
            """
            row = await conn.fetchrow(
                query,
                status.value,
                datetime.datetime.utcnow(),
                task_id,
                user_id
            )
            return VisionBoardTask(**dict(row)) if row else None

    async def get_task_with_details(self, task_id: uuid.UUID) -> Optional[VisionBoardTaskWithDetails]:
        """Get a task with all its details (comments, attachments, dependencies)"""
        async with self.pool.acquire() as conn:
            # Get task
            task_query = """
                SELECT t.id, t.genre_assignment_id, t.title, t.description, t.priority, t.status, 
                       t.due_date, t.estimated_hours, t.actual_hours, t.created_at, t.updated_at, t.created_by,
                       u.name as user_name, g.name as genre_name
                FROM tasks t
                JOIN genre_assignments ga ON t.genre_assignment_id = ga.id
                JOIN users u ON ga.user_id = u.id
                JOIN genres g ON ga.genre_id = g.id
                WHERE t.id = $1
            """
            task_row = await conn.fetchrow(task_query, task_id)
            if not task_row:
                return None

            # Get comments
            comments_query = """
                SELECT id, task_id, user_id, comment, created_at, updated_at
                FROM task_comments WHERE task_id = $1
                ORDER BY created_at ASC
            """
            comments_rows = await conn.fetch(comments_query, task_id)

            # Get attachments
            attachments_query = """
                SELECT id, task_id, file_name, file_url, file_type, file_size, uploaded_by, uploaded_at
                FROM task_attachments WHERE task_id = $1
                ORDER BY uploaded_at ASC
            """
            attachments_rows = await conn.fetch(attachments_query, task_id)

            # Get dependencies
            dependencies_query = """
                SELECT id, task_id, depends_on_task_id, dependency_type
                FROM task_dependencies WHERE task_id = $1
            """
            dependencies_rows = await conn.fetch(dependencies_query, task_id)

            task_data = dict(task_row)
            user_name = task_data.pop('user_name')
            genre_name = task_data.pop('genre_name')

            task = VisionBoardTask(**task_data)
            comments = [TaskComment(**dict(row)) for row in comments_rows]
            attachments = [TaskAttachment(**dict(row)) for row in attachments_rows]
            dependencies = [TaskDependency(**dict(row)) for row in dependencies_rows]

            return VisionBoardTaskWithDetails(
                **task.model_dump(),
                user_name=user_name,
                genre_name=genre_name,
                comments=comments,
                attachments=attachments,
                dependencies=dependencies
            )

    # Statistics and Analytics
    async def get_visionboard_summary(self, visionboard_id: uuid.UUID) -> Optional[VisionBoardSummary]:
        """Get comprehensive summary of a vision board"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    vb.id, vb.name, vb.status, vb.start_date, vb.end_date, vb.created_by,
                    COUNT(DISTINCT g.id) as total_genres,
                    COUNT(DISTINCT ga.id) as total_assignments,
                    COUNT(DISTINCT t.id) as total_tasks,
                    COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks
                FROM visionboards vb
                LEFT JOIN genres g ON vb.id = g.visionboard_id
                LEFT JOIN genre_assignments ga ON g.id = ga.genre_id
                LEFT JOIN tasks t ON ga.id = t.genre_assignment_id
                WHERE vb.id = $1
                GROUP BY vb.id, vb.name, vb.status, vb.start_date, vb.end_date, vb.created_by
            """
            row = await conn.fetchrow(query, visionboard_id)
            if not row:
                return None
            
            return VisionBoardSummary(**dict(row))

    async def get_user_stats(self, user_id: uuid.UUID) -> VisionBoardStats:
        """Get comprehensive stats for a user"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    COUNT(DISTINCT vb.id) as total_visionboards,
                    COUNT(DISTINCT CASE WHEN vb.status = 'Active' THEN vb.id END) as active_visionboards,
                    COUNT(DISTINCT CASE WHEN vb.status = 'Completed' THEN vb.id END) as completed_visionboards,
                    COUNT(DISTINCT ga.id) as total_assignments,
                    COUNT(DISTINCT CASE WHEN ga.status = 'Pending' THEN ga.id END) as pending_assignments,
                    COUNT(DISTINCT t.id) as total_tasks,
                    COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks,
                    COUNT(DISTINCT CASE WHEN t.due_date < NOW() AND t.status != 'Completed' THEN t.id END) as overdue_tasks
                FROM users u
                LEFT JOIN visionboards vb ON u.id = vb.created_by
                LEFT JOIN genre_assignments ga ON u.id = ga.user_id
                LEFT JOIN tasks t ON ga.id = t.genre_assignment_id
                WHERE u.id = $1
            """
            row = await conn.fetchrow(query, user_id)
            return VisionBoardStats(**dict(row))

    # Complex Queries (as specified in the requirements)
    async def get_visionboard_assignments(self, visionboard_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all people assigned to a vision board"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT u.name as first_name, u.name as last_name, g.name as genre, 
                       ga.status, ga.work_type, ga.payment_type, ga.payment_amount, ga.currency
                FROM users u
                JOIN genre_assignments ga ON u.id = ga.user_id
                JOIN genres g ON ga.genre_id = g.id
                WHERE g.visionboard_id = $1
                ORDER BY g.name, u.name
            """
            rows = await conn.fetch(query, visionboard_id)
            return [dict(row) for row in rows]

    async def get_user_tasks_in_visionboard(self, user_id: uuid.UUID, visionboard_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all tasks for a specific person in a vision board"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT t.title, t.description, t.status, t.due_date, t.priority, g.name as genre
                FROM tasks t
                JOIN genre_assignments ga ON t.genre_assignment_id = ga.id
                JOIN genres g ON ga.genre_id = g.id
                WHERE ga.user_id = $1 AND g.visionboard_id = $2
                ORDER BY t.due_date ASC, t.priority DESC
            """
            rows = await conn.fetch(query, user_id, visionboard_id)
            return [dict(row) for row in rows]

    async def get_visionboard_equipment_requirements(self, visionboard_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get equipment requirements for a vision board"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    e.name as equipment_name,
                    e.category,
                    e.brand,
                    e.model,
                    re.quantity,
                    re.is_provided_by_assignee,
                    re.notes,
                    re.status,
                    u.name as assigned_user_name,
                    g.name as genre_name
                FROM required_equipment re
                JOIN equipment e ON re.equipment_id = e.id
                JOIN genre_assignments ga ON re.genre_assignment_id = ga.id
                JOIN users u ON ga.user_id = u.id
                JOIN genres g ON ga.genre_id = g.id
                WHERE g.visionboard_id = $1
                ORDER BY g.name, e.category, e.name
            """
            rows = await conn.fetch(query, visionboard_id)
            return [dict(row) for row in rows]

    async def get_visionboard_users(self, visionboard_id: uuid.UUID) -> List[User]:
        """Get all users involved in a vision board (creator + assigned users)"""
        async with self.pool.acquire() as conn:
            # Get the vision board creator
            creator_query = "SELECT created_by FROM visionboards WHERE id = $1"
            creator_row = await conn.fetchrow(creator_query, visionboard_id)
            if not creator_row:
                return []
            
            creator_id = creator_row['created_by']
            
            # Get all assigned users
            assigned_users_query = """
                SELECT DISTINCT u.*
                FROM users u
                JOIN genre_assignments ga ON u.id = ga.user_id
                JOIN genres g ON ga.genre_id = g.id
                WHERE g.visionboard_id = $1
            """
            assigned_rows = await conn.fetch(assigned_users_query, visionboard_id)
            assigned_users = []
            for row in assigned_rows:
                row_dict = dict(row)
                # Parse location field
                if 'location' in row_dict and isinstance(row_dict['location'], str):
                    try:
                        row_dict['location'] = json.loads(row_dict['location'])
                    except Exception:
                        row_dict['location'] = None
                # Parse genres field
                if 'genres' in row_dict and isinstance(row_dict['genres'], str):
                    try:
                        row_dict['genres'] = json.loads(row_dict['genres'])
                    except Exception:
                        row_dict['genres'] = None
                assigned_users.append(User(**row_dict))
            
            # Get creator user details
            creator_query = "SELECT * FROM users WHERE id = $1"
            creator_row = await conn.fetchrow(creator_query, creator_id)
            creator_user = None
            if creator_row:
                creator_dict = dict(creator_row)
                # Parse location field
                if 'location' in creator_dict and isinstance(creator_dict['location'], str):
                    try:
                        creator_dict['location'] = json.loads(creator_dict['location'])
                    except Exception:
                        creator_dict['location'] = None
                # Parse genres field
                if 'genres' in creator_dict and isinstance(creator_dict['genres'], str):
                    try:
                        creator_dict['genres'] = json.loads(creator_dict['genres'])
                    except Exception:
                        creator_dict['genres'] = None
                creator_user = User(**creator_dict)
            
            # Combine creator and assigned users, removing duplicates
            all_users = assigned_users
            if creator_user and not any(user.id == creator_user.id for user in assigned_users):
                all_users.append(creator_user)
            
            return all_users

    async def get_notifications_for_user(self, user_id: uuid.UUID):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM notifications WHERE receiver_id = $1 ORDER BY created_at DESC", user_id)
            from src.models.notification import Notification
            return [Notification(**dict(row)) for row in rows]

    async def respond_to_notification(self, notification_id: uuid.UUID, responder_id: uuid.UUID, response: str, comment: str = None):
        async with self.pool.acquire() as conn:
            # Fetch the notification
            notif_row = await conn.fetchrow("SELECT * FROM notifications WHERE id = $1 AND receiver_id = $2", notification_id, responder_id)
            if not notif_row:
                return None
            # Update the notification
            await conn.execute(
                "UPDATE notifications SET status = 'read', updated_at = now() WHERE id = $1",
                notification_id
            )
            # Notify the sender (generic model)
            await self.create_notification(
                receiver_id=notif_row["sender_id"],
                sender_id=responder_id,
                object_type=notif_row["object_type"],
                object_id=notif_row["object_id"],
                event_type="response",
                data={"response": response, "comment": comment},
                message=f"User responded: {response}" + (f". Comment: {comment}" if comment else "")
            )
            from src.models.notification import Notification
            notif_row = await conn.fetchrow("SELECT * FROM notifications WHERE id = $1", notification_id)
            return Notification(**dict(notif_row)) 

    # Invitation Operations
    async def create_invitation(self, sender_id: uuid.UUID, invitation: InvitationCreate) -> Invitation:
        """Create a new invitation"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO invitations (receiver_id, sender_id, object_type, object_id, status, data)
                VALUES ($1, $2, $3, $4, 'pending', $5)
                RETURNING id, receiver_id, sender_id, object_type, object_id, status, data, created_at, responded_at
            """
            row = await conn.fetchrow(
                query,
                invitation.receiver_id,
                sender_id,
                invitation.object_type,
                invitation.object_id,
                json.dumps(invitation.data) if invitation.data else None
            )
            row_dict = dict(row)
            if isinstance(row_dict.get('data'), str):
                try:
                    row_dict['data'] = json.loads(row_dict['data'])
                except Exception:
                    row_dict['data'] = None
            return Invitation(**row_dict)

    async def get_invitations_for_user(self, user_id: uuid.UUID, status: InvitationStatus | None = None) -> list[Invitation]:
        """Get all invitations for a user (optionally filter by status)"""
        async with self.pool.acquire() as conn:
            if status:
                query = "SELECT * FROM invitations WHERE receiver_id = $1 AND status = $2 ORDER BY created_at DESC"
                rows = await conn.fetch(query, user_id, status.value)
            else:
                query = "SELECT * FROM invitations WHERE receiver_id = $1 ORDER BY created_at DESC"
                rows = await conn.fetch(query, user_id)
            invitations = []
            for row in rows:
                row_dict = dict(row)
                if isinstance(row_dict.get('data'), str):
                    try:
                        row_dict['data'] = json.loads(row_dict['data'])
                    except Exception:
                        row_dict['data'] = None
                invitations.append(Invitation(**row_dict))
            return invitations

    async def get_invitations_for_object(self, object_type: str, object_id: uuid.UUID) -> list[Invitation]:
        """Get all invitations for a given object (e.g., visionboard, genre, etc.)"""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM invitations WHERE object_type = $1 AND object_id = $2 ORDER BY created_at DESC"
            rows = await conn.fetch(query, object_type, object_id)
            invitations = []
            for row in rows:
                row_dict = dict(row)
                if isinstance(row_dict.get('data'), str):
                    try:
                        row_dict['data'] = json.loads(row_dict['data'])
                    except Exception:
                        row_dict['data'] = None
                invitations.append(Invitation(**row_dict))
            return invitations

    async def respond_to_invitation(self, invitation_id: uuid.UUID, responder_id: uuid.UUID, status: InvitationStatus, data: dict | None = None) -> Invitation | None:
        """Accept or reject an invitation (only receiver can respond)"""
        async with self.pool.acquire() as conn:
            # Only allow receiver to respond
            query = """
                UPDATE invitations
                SET status = $1, responded_at = now(), data = $2
                WHERE id = $3 AND receiver_id = $4
                RETURNING id, receiver_id, sender_id, object_type, object_id, status, data, created_at, responded_at
            """
            row = await conn.fetchrow(
                query,
                status.value,
                json.dumps(data) if data else None,
                invitation_id,
                responder_id
            )
            if not row:
                print(f"DEBUG: Invitation not found or not allowed for id={invitation_id}, responder_id={responder_id}")
                return None
            row_dict = dict(row)
            print(f"DEBUG: Invitation after update: {row_dict}")
            if isinstance(row_dict.get('data'), str):
                try:
                    row_dict['data'] = json.loads(row_dict['data'])
                except Exception:
                    row_dict['data'] = None

            # Update assignment status if this is a genre invitation
            if row_dict.get('object_type') == 'genre':
                assignment_status = None
                if status == InvitationStatus.ACCEPTED:
                    assignment_status = 'Accepted'
                elif status == InvitationStatus.REJECTED:
                    assignment_status = 'Rejected'
                if assignment_status:
                    print(f"DEBUG: Attempting to update assignment for genre_id={row_dict['object_id']} and user_id={row_dict['receiver_id']} to status={assignment_status}")
                    result = await conn.execute(
                        """
                        UPDATE genre_assignments
                        SET status = $1, responded_at = now()
                        WHERE genre_id = $2 AND user_id = $3
                        """,
                        assignment_status,
                        row_dict['object_id'],
                        row_dict['receiver_id']
                    )
                    print(f"DEBUG: Assignment update result: {result}")

            return Invitation(**row_dict)

    async def send_group_message(self, visionboard_id: uuid.UUID, sender_id: uuid.UUID, message: str) -> 'GroupMessage':
        """Send a group chat message to a vision board group."""
        async with self.pool.acquire() as conn:
            # Security: check sender is a member (creator or assigned)
            member_query = """
                SELECT 1 FROM visionboards WHERE id = $1 AND created_by = $2
                UNION
                SELECT 1 FROM genre_assignments ga
                JOIN genres g ON ga.genre_id = g.id
                WHERE g.visionboard_id = $1 AND ga.user_id = $2 AND ga.status = 'Accepted'
            """
            member = await conn.fetchrow(member_query, visionboard_id, sender_id)
            if not member:
                raise PermissionError("Not a member of this vision board group chat.")
            query = """
                INSERT INTO group_messages (visionboard_id, sender_id, message)
                VALUES ($1, $2, $3)
                RETURNING id, visionboard_id, sender_id, message, created_at
            """
            row = await conn.fetchrow(query, visionboard_id, sender_id, message)
            return GroupMessage(**dict(row))

    async def get_group_messages(self, visionboard_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50, before: datetime.datetime = None) -> list['GroupMessage']:
        """Fetch group chat messages for a vision board (paginated, newest first)."""
        async with self.pool.acquire() as conn:
            # Security: check user is a member
            member_query = """
                SELECT 1 FROM visionboards WHERE id = $1 AND created_by = $2
                UNION
                SELECT 1 FROM genre_assignments ga
                JOIN genres g ON ga.genre_id = g.id
                WHERE g.visionboard_id = $1 AND ga.user_id = $2 AND ga.status = 'Accepted'
            """
            member = await conn.fetchrow(member_query, visionboard_id, user_id)
            if not member:
                raise PermissionError("Not a member of this vision board group chat.")
            query = """
                SELECT id, visionboard_id, sender_id, message, created_at
                FROM group_messages
                WHERE visionboard_id = $1
            """
            params = [visionboard_id]
            if before:
                query += " AND created_at < $2"
                params.append(before)
            query += " ORDER BY created_at DESC LIMIT $%d" % (len(params) + 1)
            params.append(limit)
            rows = await conn.fetch(query, *params)
            return [GroupMessage(**dict(row)) for row in rows] 

    # --- Drafts ---
    async def list_drafts(self, visionboard_id: uuid.UUID) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM drafts WHERE visionboard_id = $1 ORDER BY updated_at DESC
                """, visionboard_id
            )
            return [Draft(**dict(row)) for row in rows]

    async def create_draft(self, visionboard_id: uuid.UUID, user_id: uuid.UUID, media_url: str, media_type: str = None, description: str = None):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO drafts (visionboard_id, user_id, media_url, media_type, description)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                visionboard_id, user_id, media_url, media_type, description
            )
            return Draft(**dict(row))

    async def get_draft(self, draft_id: uuid.UUID):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM drafts WHERE id = $1", draft_id
            )
            return Draft(**dict(row)) if row else None

    async def update_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID, **fields):
        if not fields:
            return await self.get_draft(draft_id)
        set_clauses = []
        values = []
        param_count = 1
        for k, v in fields.items():
            set_clauses.append(f"{k} = ${param_count}")
            values.append(v)
            param_count += 1
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(datetime.datetime.utcnow())
        param_count += 1
        values.extend([draft_id, user_id])
        query = f"""
            UPDATE drafts SET {', '.join(set_clauses)}
            WHERE id = ${param_count} AND user_id = ${param_count+1}
            RETURNING *
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return Draft(**dict(row)) if row else None

    async def delete_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM drafts WHERE id = $1 AND user_id = $2", draft_id, user_id
            )
            return result.startswith("DELETE 1")

    # --- Draft Comments ---
    async def list_draft_comments(self, draft_id: uuid.UUID) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM draft_comments WHERE draft_id = $1 ORDER BY created_at ASC", draft_id
            )
            return [DraftComment(**dict(row)) for row in rows]

    async def create_draft_comment(self, draft_id: uuid.UUID, user_id: uuid.UUID, comment: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO draft_comments (draft_id, user_id, comment)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                draft_id, user_id, comment
            )
            return DraftComment(**dict(row))

    async def update_draft_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID, comment: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE draft_comments SET comment = $1, updated_at = $2
                WHERE id = $3 AND user_id = $4
                RETURNING *
                """,
                comment, datetime.datetime.utcnow(), comment_id, user_id
            )
            return DraftComment(**dict(row)) if row else None

    async def delete_draft_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM draft_comments WHERE id = $1 AND user_id = $2", comment_id, user_id
            )
            return result.startswith("DELETE 1") 

    async def get_visionboard_collaborators(self, visionboard_id: uuid.UUID):
        """Get all collaborators (user_id, role) for a vision board. Role is the genre name."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT ga.user_id, g.name as role
                FROM genre_assignments ga
                JOIN genres g ON ga.genre_id = g.id
                WHERE g.visionboard_id = $1 AND ga.status = 'Accepted'
            """
            rows = await conn.fetch(query, visionboard_id)
            return [(row['user_id'], row['role']) for row in rows] 