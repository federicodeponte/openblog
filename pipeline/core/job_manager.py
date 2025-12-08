"""
Fire-and-Forget Async Job Manager for Blog Generation Pipeline

Handles long-running blog generation tasks (5+ minutes) with persistent tracking.
Built for production environments where quality takes time.

Features:
- Persistent job status tracking
- Fire-and-forget architecture
- Progress monitoring 
- Result retrieval
- Error handling with retries
- Job cleanup and maintenance

Architecture:
- Jobs stored in SQLite database (lightweight, no external deps)
- Background worker processes jobs asynchronously
- Client polls for status updates
- Supports batch job processing
"""

import asyncio
import json
import logging
import sqlite3
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from threading import Lock

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status states."""
    PENDING = "pending"           # Queued, not started
    RUNNING = "running"           # Currently executing
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"            # Failed with error
    CANCELLED = "cancelled"       # Manually cancelled
    TIMEOUT = "timeout"          # Exceeded time limit


@dataclass
class JobConfig:
    """Job configuration for blog generation."""
    # Required fields
    primary_keyword: str
    company_url: str
    
    # Optional fields
    language: str = "en"
    country: str = "US"
    company_name: Optional[str] = None
    company_data: Optional[Dict[str, Any]] = None
    sitemap_urls: Optional[List[str]] = None
    existing_blog_slugs: Optional[List[Dict[str, Any]]] = None
    batch_siblings: Optional[List[Dict[str, Any]]] = None
    batch_id: Optional[str] = None
    content_generation_instruction: Optional[str] = None
    word_count: Optional[int] = None
    tone: Optional[str] = None
    system_prompts: Optional[List[str]] = None
    review_prompts: Optional[List[str]] = None
    slug: Optional[str] = None
    index: bool = True
    
    # Async-specific fields
    callback_url: Optional[str] = None           # Webhook when complete
    max_duration_minutes: int = 30               # Timeout (5-30 min for quality)
    priority: int = 1                            # 1=high, 2=normal, 3=low
    client_info: Optional[Dict[str, Any]] = None # Client metadata


@dataclass
class JobResult:
    """Job execution result."""
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Progress tracking
    current_stage: Optional[str] = None          # "stage_02" etc.
    progress_percent: int = 0                    # 0-100
    stages_completed: int = 0                    # Number completed
    total_stages: int = 13                       # Total in pipeline
    
    # Results
    result_data: Optional[Dict[str, Any]] = None # Full response
    error_message: Optional[str] = None          # Error if failed
    
    # Metadata
    execution_times: Dict[str, float] = field(default_factory=dict)
    quality_score: Optional[float] = None       # AEO score if available
    retry_count: int = 0


class JobManager:
    """
    Manages async blog generation jobs with persistent storage.
    
    Provides fire-and-forget architecture for long-running content generation.
    Clients submit jobs and poll for results - no waiting required.
    """
    
    def __init__(self, db_path: str = "jobs.db", max_concurrent: int = 3):
        """
        Initialize job manager.
        
        Args:
            db_path: SQLite database path for job persistence
            max_concurrent: Maximum concurrent jobs
        """
        self.db_path = Path(db_path)
        self.max_concurrent = max_concurrent
        self._lock = Lock()
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._shutdown = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # Initialize database
        self._init_database()
        
        logger.info(f"JobManager initialized: db={db_path}, max_concurrent={max_concurrent}")
    
    def start_background_worker(self):
        """Start the background worker if not already running."""
        if self._worker_task is None or self._worker_task.done():
            try:
                self._worker_task = asyncio.create_task(self._background_worker())
                logger.info("Background worker started")
            except RuntimeError:
                # No event loop running yet - will start when needed
                logger.info("No event loop running - background worker will start later")
                pass
    
    def _init_database(self) -> None:
        """Initialize SQLite database for job persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    config TEXT NOT NULL,  -- JSON
                    result TEXT,           -- JSON
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    current_stage TEXT,
                    progress_percent INTEGER DEFAULT 0,
                    stages_completed INTEGER DEFAULT 0,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    priority INTEGER DEFAULT 2,
                    callback_url TEXT
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON jobs(priority, created_at)")
            
            conn.commit()
    
    def submit_job(self, config: JobConfig) -> str:
        """
        Submit a new blog generation job.
        
        Args:
            config: Job configuration
            
        Returns:
            job_id: Unique job identifier for tracking
        """
        job_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (
                    job_id, status, config, created_at, priority, callback_url
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                JobStatus.PENDING.value,
                json.dumps(config.__dict__),
                datetime.now().isoformat(),
                config.priority,
                config.callback_url
            ))
            conn.commit()
        
        # Ensure background worker is running
        self.start_background_worker()
        
        logger.info(f"Job submitted: {job_id} (keyword: {config.primary_keyword})")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[JobResult]:
        """
        Get current job status and results.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobResult or None if job not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            result_data = None
            if row['result']:
                try:
                    result_data = json.loads(row['result'])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid result JSON for job {job_id}")
            
            return JobResult(
                job_id=row['job_id'],
                status=JobStatus(row['status']),
                created_at=datetime.fromisoformat(row['created_at']),
                started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                duration_seconds=row['duration_seconds'],
                current_stage=row['current_stage'],
                progress_percent=row['progress_percent'] or 0,
                stages_completed=row['stages_completed'] or 0,
                result_data=result_data,
                error_message=row['error_message'],
                retry_count=row['retry_count'] or 0,
            )
    
    def list_jobs(
        self, 
        status: Optional[JobStatus] = None, 
        limit: int = 50,
        offset: int = 0
    ) -> List[JobResult]:
        """
        List jobs with optional filtering.
        
        Args:
            status: Filter by job status
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of JobResult objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if status:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE status = ? 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (status.value, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                result_data = None
                if row['result']:
                    try:
                        result_data = json.loads(row['result'])
                    except json.JSONDecodeError:
                        continue
                
                results.append(JobResult(
                    job_id=row['job_id'],
                    status=JobStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    duration_seconds=row['duration_seconds'],
                    current_stage=row['current_stage'],
                    progress_percent=row['progress_percent'] or 0,
                    stages_completed=row['stages_completed'] or 0,
                    result_data=result_data,
                    error_message=row['error_message'],
                    retry_count=row['retry_count'] or 0,
                ))
            
            return results
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled successfully
        """
        with self._lock:
            # Cancel running task if exists
            if job_id in self._running_jobs:
                task = self._running_jobs[job_id]
                if not task.done():
                    task.cancel()
                del self._running_jobs[job_id]
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE jobs 
                SET status = ?, completed_at = ? 
                WHERE job_id = ? AND status IN (?, ?)
            """, (
                JobStatus.CANCELLED.value,
                datetime.now().isoformat(),
                job_id,
                JobStatus.PENDING.value,
                JobStatus.RUNNING.value
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
        
        if success:
            logger.info(f"Job cancelled: {job_id}")
        
        return success
    
    async def _background_worker(self) -> None:
        """Background worker to process pending jobs."""
        logger.info("Background worker started")
        
        while not self._shutdown:
            try:
                await self._process_pending_jobs()
                await self._cleanup_completed_jobs()
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Background worker error: {e}", exc_info=True)
                await asyncio.sleep(10)  # Longer delay on error
    
    async def _process_pending_jobs(self) -> None:
        """Process pending jobs up to max_concurrent limit."""
        with self._lock:
            running_count = len([t for t in self._running_jobs.values() if not t.done()])
            
            if running_count >= self.max_concurrent:
                return
            
            slots_available = self.max_concurrent - running_count
        
        # Get pending jobs ordered by priority and creation time
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT job_id, config FROM jobs 
                WHERE status = ? 
                ORDER BY priority ASC, created_at ASC 
                LIMIT ?
            """, (JobStatus.PENDING.value, slots_available))
            
            pending_jobs = cursor.fetchall()
        
        for job_row in pending_jobs:
            job_id = job_row['job_id']
            
            try:
                config_dict = json.loads(job_row['config'])
                config = JobConfig(**config_dict)
                
                # Mark as running
                self._update_job_status(job_id, JobStatus.RUNNING, started_at=datetime.now())
                
                # Start async task
                task = asyncio.create_task(self._execute_job(job_id, config))
                
                with self._lock:
                    self._running_jobs[job_id] = task
                
                logger.info(f"Started job: {job_id} (keyword: {config.primary_keyword})")
                
            except Exception as e:
                logger.error(f"Failed to start job {job_id}: {e}")
                self._update_job_status(
                    job_id, 
                    JobStatus.FAILED, 
                    error_message=f"Startup error: {str(e)}",
                    completed_at=datetime.now()
                )
    
    async def _execute_job(self, job_id: str, config: JobConfig) -> None:
        """Execute a single blog generation job."""
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from pipeline.core import WorkflowEngine, create_production_pipeline_stages
            
            # Create workflow engine with progress tracking
            engine = WorkflowEngine()
            engine.register_stages(create_production_pipeline_stages())
            
            # Create progress tracker
            progress_tracker = self._create_progress_tracker(job_id, total_stages=13)
            
            # Build job config dict
            job_config = {
                "primary_keyword": config.primary_keyword,
                "company_url": config.company_url,
                "language": config.language,
                "country": config.country,
                "index": config.index,
            }
            
            # Add optional fields
            for field in ['company_name', 'company_data', 'sitemap_urls', 
                         'existing_blog_slugs', 'batch_siblings', 'batch_id',
                         'content_generation_instruction', 'word_count', 'tone', 
                         'system_prompts', 'review_prompts', 'slug']:
                value = getattr(config, field)
                if value is not None:
                    job_config[field] = value
            
            # Execute workflow with progress tracking
            context = await self._execute_with_progress(
                engine, job_id, job_config, progress_tracker
            )
            
            # Build response data
            duration = time.time() - start_time
            
            # Create a mock request for response building
            from service.api import BlogGenerationRequest, build_response_from_context
            
            mock_request = BlogGenerationRequest(
                primary_keyword=config.primary_keyword,
                company_url=config.company_url,
                language=config.language,
                country=config.country,
                company_name=config.company_name,
                index=config.index,
            )
            
            response = build_response_from_context(
                context=context,
                request=mock_request, 
                job_id=job_id,
                duration=duration,
            )
            
            # Store results
            result_data = response.model_dump()
            quality_score = result_data.get('aeo_score')
            
            self._update_job_status(
                job_id,
                JobStatus.COMPLETED,
                completed_at=datetime.now(),
                duration_seconds=duration,
                result_data=result_data,
                quality_score=quality_score,
                progress_percent=100,
                stages_completed=13
            )
            
            # Update Supabase if client_info contains Supabase integration details
            if config.client_info and config.client_info.get('article_id'):
                await self._update_supabase_article(job_id, config, response)
            
            # Call webhook if configured
            if config.callback_url:
                await self._call_webhook(config.callback_url, job_id, response.model_dump())
            
            logger.info(f"Job completed: {job_id} in {duration:.1f}s (AEO: {quality_score})")
            
        except asyncio.CancelledError:
            logger.info(f"Job cancelled: {job_id}")
            self._update_job_status(job_id, JobStatus.CANCELLED, completed_at=datetime.now())
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Job failed: {job_id} after {duration:.1f}s - {error_msg}")
            logger.error(traceback.format_exc())
            
            # Report error to error monitoring system
            from .error_handling import error_classifier, error_reporter
            error_context = error_classifier.classify_error(e, "job_execution")
            error_context.job_id = job_id
            error_context.metadata = {
                "duration_seconds": duration,
                "primary_keyword": config.primary_keyword,
                "company_url": config.company_url
            }
            error_reporter.report_error(error_context)
            
            self._update_job_status(
                job_id,
                JobStatus.FAILED,
                completed_at=datetime.now(),
                duration_seconds=duration,
                error_message=error_msg[:1000]  # Truncate long errors
            )
        
        finally:
            # Clean up running jobs tracking
            with self._lock:
                if job_id in self._running_jobs:
                    del self._running_jobs[job_id]
    
    def _create_progress_tracker(self, job_id: str, total_stages: int):
        """Create progress tracking callback for workflow engine."""
        def update_progress(stage_name: str, stage_num: int, completed: bool = False):
            if completed:
                progress_percent = int((stage_num + 1) / total_stages * 100)
                self._update_job_progress(
                    job_id, 
                    current_stage=stage_name,
                    progress_percent=progress_percent,
                    stages_completed=stage_num + 1
                )
        
        return update_progress
    
    async def _execute_with_progress(
        self, 
        engine, 
        job_id: str, 
        job_config: Dict[str, Any], 
        progress_tracker
    ):
        """Execute workflow with progress tracking using native callback support."""
        # Use the native progress callback support in WorkflowEngine
        context = await engine.execute(
            job_id=job_id, 
            job_config=job_config, 
            progress_callback=progress_tracker
        )
        
        return context
    
    def _update_job_status(
        self, 
        job_id: str, 
        status: JobStatus,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        quality_score: Optional[float] = None,
        progress_percent: Optional[int] = None,
        stages_completed: Optional[int] = None
    ) -> None:
        """Update job status in database."""
        with sqlite3.connect(self.db_path) as conn:
            updates = ["status = ?"]
            values = [status.value]
            
            if started_at:
                updates.append("started_at = ?")
                values.append(started_at.isoformat())
            
            if completed_at:
                updates.append("completed_at = ?")
                values.append(completed_at.isoformat())
            
            if duration_seconds is not None:
                updates.append("duration_seconds = ?")
                values.append(duration_seconds)
            
            if result_data is not None:
                updates.append("result = ?")
                values.append(json.dumps(result_data))
            
            if error_message is not None:
                updates.append("error_message = ?")
                values.append(error_message)
            
            if progress_percent is not None:
                updates.append("progress_percent = ?")
                values.append(progress_percent)
            
            if stages_completed is not None:
                updates.append("stages_completed = ?")
                values.append(stages_completed)
            
            values.append(job_id)
            
            conn.execute(f"""
                UPDATE jobs SET {', '.join(updates)}
                WHERE job_id = ?
            """, values)
            
            conn.commit()
    
    def _update_job_progress(
        self,
        job_id: str,
        current_stage: Optional[str] = None,
        progress_percent: Optional[int] = None,
        stages_completed: Optional[int] = None
    ) -> None:
        """Update job progress without changing status."""
        with sqlite3.connect(self.db_path) as conn:
            updates = []
            values = []
            
            if current_stage:
                updates.append("current_stage = ?")
                values.append(current_stage)
            
            if progress_percent is not None:
                updates.append("progress_percent = ?")
                values.append(progress_percent)
            
            if stages_completed is not None:
                updates.append("stages_completed = ?")
                values.append(stages_completed)
            
            if updates:
                values.append(job_id)
                conn.execute(f"""
                    UPDATE jobs SET {', '.join(updates)}
                    WHERE job_id = ?
                """, values)
                conn.commit()
    
    async def _update_supabase_article(
        self, 
        job_id: str, 
        config: JobConfig, 
        response: Any
    ) -> None:
        """Update Supabase article after job completion."""
        try:
            import os
            client_info = config.client_info or {}
            article_id = client_info.get('article_id')
            # Use client_info if provided, otherwise fall back to environment variables
            supabase_url = client_info.get('supabase_url') or os.getenv("SUPABASE_URL")
            supabase_service_key = client_info.get('supabase_service_key') or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not article_id:
                logger.warning(f"[{job_id}] Missing article_id in client_info")
                return
            
            if not supabase_url or not supabase_service_key:
                logger.warning(f"[{job_id}] Missing Supabase credentials (not in client_info or environment variables)")
                return
            
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_service_key)
            
            # Build update data from response
            update_data = {
                'title': response.headline or config.primary_keyword,
                'headline': response.headline,
                'slug': response.slug,
                'html_content': response.html_content,
                'direct_answer': response.direct_answer,
                'intro': response.intro,
                'teaser': response.teaser,
                'word_count': response.quality_report.metrics.word_count if response.quality_report else None,
                'generation_status': 'completed',
                'generation_error': None,
                'status': 'in_review',  # Move from 'drafting' to 'in_review'
                'updated_at': datetime.now().isoformat(),
            }
            
            # Store sections, FAQ, etc. in prompts JSONB
            if response.sections or response.faq or response.paa:
                update_data['prompts'] = {
                    'sections': [s.model_dump() if hasattr(s, 'model_dump') else s for s in (response.sections or [])],
                    'faq': [f.model_dump() if hasattr(f, 'model_dump') else f for f in (response.faq or [])],
                    'paa': [p.model_dump() if hasattr(p, 'model_dump') else p for p in (response.paa or [])],
                    'key_takeaways': response.key_takeaways or [],
                    'meta_title': response.meta_title,
                    'meta_description': response.meta_description,
                    'quality_report': response.quality_report.model_dump() if response.quality_report else None,
                }
            
            # Image data
            if response.image_url:
                update_data['image_url'] = response.image_url
                update_data['image_alt_text'] = response.image_alt_text
                update_data['image_drive_id'] = response.image_drive_id
            
            # Update article
            supabase.table('articles').update(update_data).eq('id', article_id).execute()
            
            # Generate and store embedding
            try:
                embedding = await self._generate_content_embedding(
                    headline=response.headline,
                    intro=response.intro,
                    direct_answer=response.direct_answer,
                    teaser=response.teaser,
                    html_content=response.html_content,
                )
                if embedding and len(embedding) > 0:
                    supabase.table('articles').update({
                        'content_embedding': embedding,
                        'embedded_at': datetime.now().isoformat(),
                    }).eq('id', article_id).execute()
                    logger.info(f"[{job_id}] Content embedding stored")
            except Exception as embed_err:
                logger.warning(f"[{job_id}] Failed to generate embedding: {embed_err}")
            
            # Mark keyword as written
            keyword_id = client_info.get('keyword_id')
            if keyword_id:
                supabase.table('keywords').update({
                    'written': True,
                    'updated_at': datetime.now().isoformat(),
                }).eq('id', keyword_id).execute()
            
            logger.info(f"[{job_id}] Supabase article {article_id} updated successfully")
            
        except Exception as e:
            logger.error(f"[{job_id}] Failed to update Supabase article: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _generate_content_embedding(
        self,
        headline: Optional[str] = None,
        intro: Optional[str] = None,
        direct_answer: Optional[str] = None,
        teaser: Optional[str] = None,
        html_content: Optional[str] = None,
    ) -> Optional[List[float]]:
        """Generate content embedding for semantic deduplication."""
        try:
            import httpx
            import re
            
            EMBEDDER_ENDPOINT = "https://clients--content-embedder-fastapi-app.modal.run"
            
            # Build embedding text
            parts: List[str] = []
            if headline:
                parts.append(headline)
                parts.append(headline)  # Weight 2x
            if direct_answer:
                parts.append(direct_answer)
            if intro:
                parts.append(intro)
            if teaser:
                parts.append(teaser)
            if html_content:
                text_content = html_content
                text_content = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', ' ', text_content, flags=re.IGNORECASE)
                text_content = re.sub(r'<style\b[^>]*>[\s\S]*?</style>', ' ', text_content, flags=re.IGNORECASE)
                text_content = re.sub(r'<[^>]+>', ' ', text_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                if text_content:
                    parts.append(text_content)
            
            full_text = " ".join(parts).strip()
            if not full_text:
                return None
            
            # Truncate to ~2000 tokens
            max_chars = 8000
            if len(full_text) > max_chars:
                full_text = full_text[:max_chars]
                last_period = full_text.rfind('.')
                if last_period > max_chars * 0.8:
                    full_text = full_text[:last_period + 1]
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{EMBEDDER_ENDPOINT}/embed",
                    json={
                        "texts": [full_text],
                        "task_type": "SEMANTIC_SIMILARITY",
                    },
                )
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                if embeddings and len(embeddings) > 0:
                    return embeddings[0]
            
            return None
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None
    
    async def _call_webhook(self, webhook_url: str, job_id: str, result_data: Dict[str, Any]) -> None:
        """Call webhook URL with job completion data."""
        try:
            import httpx
            
            payload = {
                "job_id": job_id,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "result": result_data
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                
            logger.info(f"Webhook called successfully for job {job_id}")
            
        except Exception as e:
            logger.error(f"Webhook failed for job {job_id}: {e}")
    
    async def _cleanup_completed_jobs(self) -> None:
        """Clean up old completed/failed jobs to prevent database bloat."""
        cutoff_date = datetime.now() - timedelta(days=7)  # Keep 1 week
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM jobs 
                WHERE status IN (?, ?, ?) 
                AND completed_at < ?
            """, (
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
                cutoff_date.isoformat()
            ))
            
            if cursor.rowcount > 0:
                logger.info(f"Cleaned up {cursor.rowcount} old jobs")
                conn.commit()
    
    def shutdown(self) -> None:
        """Gracefully shutdown the job manager."""
        logger.info("Shutting down job manager...")
        self._shutdown = True
        
        # Cancel all running jobs
        with self._lock:
            for job_id, task in self._running_jobs.items():
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled running job: {job_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job manager statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM jobs
                GROUP BY status
            """)
            
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get running count from memory
            with self._lock:
                running_count = len([t for t in self._running_jobs.values() if not t.done()])
            
            cursor = conn.execute("""
                SELECT AVG(duration_seconds) as avg_duration
                FROM jobs
                WHERE status = ? AND duration_seconds IS NOT NULL
            """, (JobStatus.COMPLETED.value,))
            
            avg_duration = cursor.fetchone()[0] or 0
            
            return {
                "status_counts": status_counts,
                "running_jobs": running_count,
                "max_concurrent": self.max_concurrent,
                "avg_duration_seconds": avg_duration,
                "database_path": str(self.db_path),
            }


# Global job manager instance
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get or create global job manager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager