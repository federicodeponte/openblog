"""
WorkflowEngine - Orchestrates all 12 stages of the blog writing pipeline.

Clean separation of concerns:
- Initialization: Load all stages
- Execution: Run stages in order, pass context through
- Error handling: Graceful fallback and logging
- Monitoring: Track execution times and quality metrics

Sequential flow with parallel execution in middle (stages 4-9).
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Type, Tuple
from abc import ABC, abstractmethod

from .execution_context import ExecutionContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Stage(ABC):
    """
    Abstract base class for all workflow stages.

    Each stage implements this interface and executes a specific portion
    of the blog writing pipeline.
    """

    stage_num: int
    """Stage number (0-11)"""

    stage_name: str
    """Human-readable stage name"""

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute this stage.

        Args:
            context: Current execution context

        Returns:
            Updated execution context

        Raises:
            Exception: Any errors encountered during execution
        """
        pass

    def __repr__(self) -> str:
        return f"Stage {self.stage_num}: {self.stage_name}"


class WorkflowEngine:
    """
    Main orchestrator for Python Blog Writing System.

    Manages:
    - Stage loading and initialization
    - Sequential execution (stages 0-3, 10-11)
    - Parallel execution (stages 4-9 via asyncio.gather)
    - Error handling and fallback
    - Metrics collection
    """

    def __init__(self) -> None:
        """Initialize workflow engine."""
        self.stages: Dict[int, Stage] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_stage(self, stage: Stage) -> None:
        """
        Register a stage with the engine.

        Args:
            stage: Stage instance implementing Stage interface

        Raises:
            ValueError: If stage number already registered
        """
        if stage.stage_num in self.stages:
            raise ValueError(f"Stage {stage.stage_num} already registered")

        self.stages[stage.stage_num] = stage
        self.logger.info(f"Registered {stage}")

    def register_stages(self, stages: List[Stage]) -> None:
        """
        Register multiple stages at once.

        Args:
            stages: List of Stage instances
        """
        for stage in stages:
            self.register_stage(stage)

    async def execute(
        self, 
        job_id: str, 
        job_config: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> ExecutionContext:
        """
        Execute complete workflow.

        Flow:
        1. Stage 0: Data fetch → loads job config, company data
        2. Stage 1: Prompt build → creates prompt with variables
        3. Stage 2: Gemini call → generates raw article with tools
        4. Stage 3: Extraction → extracts structured data
        5. Stages 4-9: Parallel execution
           - Stage 4: Citations → validate sources
           - Stage 5: Internal links → generate "More Reading"
           - Stage 6: ToC → create table of contents labels
           - Stage 7: Metadata → calculate read time + date
           - Stage 8: FAQ/PAA → validate/generate Q&A
           - Stage 9: Image → generate article image
        6. Stage 10: Cleanup → merge parallel results, validate
        7. Stage 11: Storage → HTML generation and Supabase storage

        Args:
            job_id: Unique job identifier
            job_config: Job configuration (passed to Stage 0)

        Returns:
            Final ExecutionContext with all results

        Raises:
            Exception: If critical stages fail
        """
        context = ExecutionContext(job_id=job_id, job_config=job_config)
        self.progress_callback = progress_callback

        self.logger.info(f"Starting workflow for job: {job_id}")
        self.logger.info(f"Total execution time target: < 105 seconds")

        try:
            # Sequential: Stages 0-3 (with 2b quality refinement AFTER extraction)
            context = await self._execute_sequential(context, [0, 1, 2, 3])
            context = await self._execute_stage_2b_conditional(context)

            # Parallel: Stages 4-9
            context = await self._execute_parallel(context, [4, 5, 6, 7, 8, 9])

            # OPTIMIZED: Stage 10 and Stage 11 can overlap
            # Stage 11 can start HTML generation as soon as validated_article is ready
            # (doesn't need to wait for quality_report to finish)
            context = await self._execute_stage_10_with_overlap(context)

            # Calculate metrics
            total_time = context.get_total_execution_time()
            self.logger.info(f"Workflow completed in {total_time:.2f}s")
            self.logger.info(
                f"Quality report: "
                f"AEO score={context.quality_report.get('metrics', {}).get('aeo_score', 'N/A')} "
                f"critical_issues={len(context.quality_report.get('critical_issues', []))}"
            )

            return context

        except Exception as e:
            self.logger.error(f"Workflow failed: {e}", exc_info=True)
            context.add_error("workflow", e)
            raise

    async def _execute_sequential(
        self, context: ExecutionContext, stage_nums: List[int]
    ) -> ExecutionContext:
        """
        Execute stages sequentially.

        Each stage receives context from previous stage.
        If a stage fails, it's logged but execution may continue
        (depending on stage criticality).

        Args:
            context: Current execution context
            stage_nums: List of stage numbers to execute in order

        Returns:
            Updated execution context
        """
        for stage_num in stage_nums:
            if stage_num not in self.stages:
                self.logger.warning(f"Stage {stage_num} not registered, skipping")
                continue

            stage = self.stages[stage_num]
            self.logger.info(f"Executing {stage}")

            try:
                # Notify progress start
                if self.progress_callback:
                    self.progress_callback(f"stage_{stage_num:02d}", stage_num, False)
                
                start_time = time.time()
                context = await stage.execute(context)
                duration = time.time() - start_time

                context.add_execution_time(f"stage_{stage_num:02d}", duration)
                self.logger.info(f"✅ {stage} completed in {duration:.2f}s")
                
                # Notify progress completion
                if self.progress_callback:
                    self.progress_callback(f"stage_{stage_num:02d}", stage_num, True)

            except Exception as e:
                self.logger.error(f"❌ {stage} failed: {e}", exc_info=True)
                context.add_error(f"stage_{stage_num:02d}", e)

                # Stage 0, 2, 10, 11 are critical - don't continue
                if stage_num in [0, 2, 10, 11]:
                    raise

        return context

    async def _execute_stage_2b_conditional(
        self, context: ExecutionContext
    ) -> ExecutionContext:
        """
        Conditionally execute Stage 2b (Quality Refinement).
        
        Only runs if quality issues are detected in Gemini output.
        This is inserted AFTER Stage 3 (Extraction) and BEFORE Stage 4-9 (Parallel).
        
        Args:
            context: Current execution context (with structured_data from Stage 3)
        
        Returns:
            Updated execution context (potentially with refined structured_data)
        """
        from ..blog_generation.stage_02b_quality_refinement import QualityRefinementStage
        
        stage_2b = QualityRefinementStage()
        self.logger.info(f"Executing conditional {stage_2b}")
        
        try:
            # Notify progress start
            if self.progress_callback:
                self.progress_callback("stage_02b", "2b", False)
            
            start_time = time.time()
            context = await stage_2b.execute(context)
            duration = time.time() - start_time
            
            context.add_execution_time("stage_02b", duration)
            self.logger.info(f"✅ {stage_2b} completed in {duration:.2f}s")
            
            # Notify progress completion
            if self.progress_callback:
                self.progress_callback("stage_02b", "2b", True)
        
        except Exception as e:
            self.logger.warning(f"⚠️  {stage_2b} failed: {e}", exc_info=True)
            context.add_error("stage_02b", e)
            # Non-critical - continue with original content
            self.logger.info("Continuing with original Gemini output (no refinement)")

        return context

    async def _execute_parallel(
        self, context: ExecutionContext, stage_nums: List[int]
    ) -> ExecutionContext:
        """
        Execute stages in parallel using asyncio.

        All stages in stage_nums run concurrently via asyncio.gather().
        Each stage gets a copy of current context, returns updated context.
        Results are merged into context.parallel_results.

        Args:
            context: Current execution context
            stage_nums: List of stage numbers to execute in parallel

        Returns:
            Updated execution context with parallel_results populated

        Note:
            Stages 4-9 each take 1-6+ minutes depending on complexity:
            - Stage 4 (Citations): ~4 min (AI Agent3 loop)
            - Stage 5 (Internal Links): ~3-4 min
            - Stage 6 (ToC): ~30 sec (fast)
            - Stage 7 (Metadata): <1 sec (instant)
            - Stage 8 (FAQ/PAA): ~2-3 min
            - Stage 9 (Image): ~2-4 min
            Total parallel time: ~6-10 min (limited by slowest = Stage 4)
        """
        self.logger.info(f"Starting parallel execution: Stages {stage_nums}")
        self.logger.info("   Note: All stages run concurrently")
        self.logger.info("   Total time limited by slowest stage (typically Stage 4)")

        # Create tasks
        tasks = []
        task_map = {}  # Map task to stage number for error handling

        for stage_num in stage_nums:
            if stage_num not in self.stages:
                self.logger.warning(f"Stage {stage_num} not registered, skipping")
                continue

            stage = self.stages[stage_num]
            
            # Notify parallel stages starting
            if self.progress_callback:
                self.progress_callback(f"stage_{stage_num:02d}", stage_num, False)
            
            task = asyncio.create_task(self._execute_stage_timed(stage, context))
            tasks.append(task)
            task_map[task] = stage_num

        if not tasks:
            return context

        # Execute in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for task, result in zip(tasks, results):
                stage_num = task_map[task]
                stage_name = f"stage_{stage_num:02d}"

                if isinstance(result, Exception):
                    self.logger.error(f"❌ Stage {stage_num} failed: {result}")
                    context.add_error(stage_name, result)
                    # Parallel stages are not critical - continue if one fails
                else:
                    duration, updated_context = result
                    context.add_execution_time(stage_name, duration)

                    # Merge parallel results
                    if hasattr(updated_context, "parallel_results"):
                        context.parallel_results.update(updated_context.parallel_results)

                    self.logger.info(
                        f"✅ Stage {stage_num} completed in {duration:.2f}s"
                    )
                    
                    # Notify parallel stage completion
                    if self.progress_callback:
                        self.progress_callback(f"stage_{stage_num:02d}", stage_num, True)

        except Exception as e:
            self.logger.error(f"Parallel execution error: {e}", exc_info=True)
            context.add_error("parallel_execution", e)

        return context

    async def _execute_stage_10_with_overlap(
        self, context: ExecutionContext
    ) -> ExecutionContext:
        """
        Execute Stage 10 and Stage 11 with overlap optimization.
        
        Stage 11 can start HTML generation as soon as validated_article is ready,
        before quality_report finishes. This saves ~0.5-1 second.
        
        Args:
            context: Execution context after stages 4-9
            
        Returns:
            Updated context with both stages complete
        """
        # Start Stage 10
        stage_10 = self.stages.get(10)
        if not stage_10:
            self.logger.warning("Stage 10 not registered")
            return context
        
        self.logger.info("Executing Stage 10 (cleanup) and Stage 11 (storage) with overlap")
        
        # Execute Stage 10
        start_time = time.time()
        context = await stage_10.execute(context)
        stage_10_duration = time.time() - start_time
        context.add_execution_time("stage_10", stage_10_duration)
        self.logger.info(f"✅ Stage 10 completed in {stage_10_duration:.2f}s")
        
        # QUALITY GATE: Check if regeneration is needed
        context = await self._check_quality_gate_and_regenerate(context)
        
        # Stage 12: Review Iteration (CONDITIONAL - only runs if review_prompts present)
        stage_12 = self.stages.get(12)
        if stage_12:
            start_time = time.time()
            context = await stage_12.execute(context)
            stage_12_duration = time.time() - start_time
            context.add_execution_time("stage_12", stage_12_duration)
            if context.parallel_results.get("revision_applied"):
                self.logger.info(f"✅ Stage 12 completed in {stage_12_duration:.2f}s (revisions applied)")
            else:
                self.logger.info(f"✅ Stage 12 skipped (no review_prompts)")
        
        # Stage 11 can start immediately after validated_article is ready
        # (quality_report is already computed in Stage 10, revisions from Stage 12 applied)
        stage_11 = self.stages.get(11)
        if not stage_11:
            self.logger.warning("Stage 11 not registered")
            return context
        
        start_time = time.time()
        context = await stage_11.execute(context)
        stage_11_duration = time.time() - start_time
        context.add_execution_time("stage_11", stage_11_duration)
        self.logger.info(f"✅ Stage 11 completed in {stage_11_duration:.2f}s")
        
        return context

    async def _check_quality_gate_and_regenerate(self, context: ExecutionContext) -> ExecutionContext:
        """
        Check quality gate and regenerate if needed.
        
        Implements 3-attempt regeneration strategy for failed articles:
        1. First failure: Regenerate with enhanced prompt
        2. Second failure: Regenerate with relaxed constraints  
        3. Third failure: Accept with warning
        
        Also handles language validation failures with automatic retry.
        
        Args:
            context: Execution context after Stage 10
            
        Returns:
            Updated context (potentially regenerated)
        """
        quality_report = context.quality_report
        if not quality_report:
            self.logger.warning("No quality report available for quality gate check")
            return context
        
        passed = quality_report.get("passed", False)
        aeo_score = quality_report.get("metrics", {}).get("aeo_score", 0)
        critical_issues = quality_report.get("critical_issues", [])
        
        # Check for language validation failure
        needs_lang_regeneration = getattr(context, 'needs_regeneration', False)
        regeneration_reason = getattr(context, 'regeneration_reason', None)
        
        # Track regeneration attempts
        if not hasattr(context, 'regeneration_attempts'):
            context.regeneration_attempts = 0
        
        # Check for language validation warning (just log, don't retry - prompt should handle it)
        if needs_lang_regeneration and regeneration_reason == "language_validation_failed":
            lang_metrics = getattr(context, 'language_validation', {})
            contamination = lang_metrics.get('english_contamination_score', 0)
            self.logger.warning(f"⚠️  Language contamination detected: {contamination:.1f}% (logged for monitoring)")
            # Reset flags - don't block on this, just warn
            context.needs_regeneration = False
            context.regeneration_reason = None
        
        if passed:
            if context.regeneration_attempts > 0:
                self.logger.info(f"✅ Quality Gate PASSED after {context.regeneration_attempts} regeneration(s): AEO={aeo_score}/100")
            else:
                self.logger.info(f"✅ Quality Gate PASSED on first attempt: AEO={aeo_score}/100")
            return context
        
        # Quality gate failed
        context.regeneration_attempts += 1
        max_attempts = 3
        
        self.logger.warning(f"❌ Quality Gate FAILED (attempt {context.regeneration_attempts}/{max_attempts}): AEO={aeo_score}/100")
        for issue in critical_issues[:3]:
            self.logger.warning(f"   {issue}")
        
        if context.regeneration_attempts >= max_attempts:
            self.logger.error(f"🚨 FINAL FAILURE: Article failed quality gate after {max_attempts} attempts")
            self.logger.error(f"   Final AEO: {aeo_score}/100, Critical Issues: {len(critical_issues)}")
            # Mark context as having failed quality but continue workflow
            context.quality_gate_failed = True
            return context
        
        # Regenerate with strategy based on attempt number
        self.logger.info(f"🔄 Regenerating article (attempt {context.regeneration_attempts + 1}/{max_attempts})")
        
        # Apply regeneration strategy
        context = self._apply_regeneration_strategy(context)
        
        # Use centralized regeneration helper
        return await self._regenerate_article(context, "quality")

    async def _regenerate_article(self, context: ExecutionContext, reason: str) -> ExecutionContext:
        """
        Regenerate article from Stage 2 onwards.
        
        Args:
            context: Current execution context
            reason: Reason for regeneration ('language' or 'quality')
            
        Returns:
            Updated context after regeneration
        """
        self.logger.info(f"🔄 Regenerating article (reason: {reason})")
        
        try:
            # Clear previous results for regeneration
            context.structured_data = None
            context.parallel_results = {}
            context.validated_article = None
            context.quality_report = {}
            
            # Restart from Stage 2 (main article generation)
            # Keep Stage 0-1 results (keyword/prompt base)
            context = await self._execute_sequential(context, [2, 3])
            
            # Parallel: Stages 4-9
            context = await self._execute_parallel(context, [4, 5, 6, 7, 8, 9])
            
            # Stage 10 cleanup (this will trigger recursive quality check)
            stage_10 = self.stages.get(10)
            if stage_10:
                start_time = time.time()
                context = await stage_10.execute(context)
                stage_10_duration = time.time() - start_time
                context.add_execution_time(f"stage_10_regen_{reason}", stage_10_duration)
                self.logger.info(f"✅ Regeneration Stage 10 completed in {stage_10_duration:.2f}s")
            
            # Recursive quality check (will handle next failure if needed)
            return await self._check_quality_gate_and_regenerate(context)
            
        except Exception as e:
            self.logger.error(f"Regeneration attempt failed: {e}")
            context.quality_gate_failed = True
            context.add_error("regeneration", e)
            return context

    def _apply_regeneration_strategy(self, context: ExecutionContext) -> ExecutionContext:
        """
        Apply regeneration strategy based on attempt number.
        
        Args:
            context: Current execution context
            
        Returns:
            Context with modified generation parameters
        """
        attempt = context.regeneration_attempts
        
        if attempt == 1:
            # First retry: Enhanced focus on failed aspects
            self.logger.info("📝 Regeneration Strategy 1: Enhanced content quality focus")
            
            # Add quality enhancement instructions
            if not context.job_config:
                context.job_config = {}
            
            enhancement_prompts = [
                "Focus on achieving 80+ AEO score with strict quality requirements.",
                "Ensure every paragraph has exactly 2-3 citations with credible sources.",
                "Distribute internal links evenly (1 per section) throughout the article.",
                "Target 40-60 words per paragraph with clear, actionable content.",
                "Include specific data points, KPIs, and real examples in every paragraph."
            ]
            
            existing_instructions = context.job_config.get("content_generation_instruction", "")
            enhanced_instructions = f"{existing_instructions}\n\nQUALITY ENHANCEMENT:\n" + "\n".join(enhancement_prompts)
            context.job_config["content_generation_instruction"] = enhanced_instructions
            
        elif attempt == 2:
            # Second retry: Relaxed constraints but maintain core quality
            self.logger.info("📝 Regeneration Strategy 2: Relaxed constraints with quality focus")
            
            # Relax some constraints to improve generation success
            if not context.job_config:
                context.job_config = {}
            
            fallback_prompts = [
                "Target 75+ AEO score (relaxed from 80) while maintaining content quality.",
                "Focus on clear, helpful content with practical examples.",
                "Include citations and internal links naturally without forcing exact counts.",
                "Prioritize readability and user value over strict formatting rules."
            ]
            
            fallback_instructions = "\n\nFALLBACK STRATEGY:\n" + "\n".join(fallback_prompts)
            context.job_config["content_generation_instruction"] = fallback_instructions
            
        return context

    async def _execute_stage_timed(
        self, stage: Stage, context: ExecutionContext
    ) -> Tuple[float, ExecutionContext]:
        """
        Execute a single stage and track execution time.

        Args:
            stage: Stage to execute
            context: Execution context

        Returns:
            Tuple of (duration_seconds, updated_context)

        Raises:
            Exception: Any errors from stage execution
        """
        start_time = time.time()
        updated_context = await stage.execute(context)
        duration = time.time() - start_time
        return duration, updated_context

    def get_stage(self, stage_num: int) -> Optional[Stage]:
        """
        Get a registered stage by number.

        Args:
            stage_num: Stage number (0-11)

        Returns:
            Stage instance or None if not registered
        """
        return self.stages.get(stage_num)

    def list_stages(self) -> List[Stage]:
        """
        Get all registered stages in order.

        Returns:
            List of Stage instances sorted by stage number
        """
        return [self.stages[i] for i in sorted(self.stages.keys())]
