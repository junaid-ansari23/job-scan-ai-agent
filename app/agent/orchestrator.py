from uuid import uuid4

from app.agent.models import AgentStage, AgentState, RunStatus, ToolStatus
from app.agent.tool_registry import RegisteredTool, ToolRegistry
from app.models.domain import EvaluationResult, JobOpportunity
from app.models.email import EmailMessage
from app.models.preferences import Preferences
from app.services.evaluation import evaluate_job
from app.services.job_extractor import JobExtractor

EXTRACT_TOOL = "extract_job_information"
EVALUATE_TOOL = "evaluate_job"


class JobTriageOrchestrator:
    """Bounded single-message state machine for the V1 agent flow.

    Tool selection is deterministic in Day 4: extraction must precede
    evaluation. Keeping selection in this small method makes later model-driven
    selection replaceable without weakening the registry allow list, dry-run
    block, iteration guard, or typed state transitions.
    """

    def __init__(
        self,
        extractor: JobExtractor,
        preferences: Preferences,
        *,
        max_iterations: int = 4,
        dry_run: bool = True,
        registry: ToolRegistry | None = None,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        self._extractor = extractor
        self._preferences = preferences
        self._max_iterations = max_iterations
        self._dry_run = dry_run
        self._registry = registry or self._build_registry()

    def _build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(
            RegisteredTool(name=EXTRACT_TOOL, handler=self._extractor.extract)
        )
        registry.register(
            RegisteredTool(
                name=EVALUATE_TOOL,
                handler=lambda opportunity: evaluate_job(opportunity, self._preferences),
            )
        )
        return registry

    def process(self, message: EmailMessage) -> AgentState:
        state = AgentState(
            run_id=str(uuid4()),
            message_id=message.message_id,
            max_iterations=self._max_iterations,
            dry_run=self._dry_run,
        )

        while state.status == RunStatus.RUNNING:
            if state.iteration_count >= state.max_iterations:
                state.status = RunStatus.ITERATION_LIMIT
                state.error_code = "MAX_ITERATIONS_EXCEEDED"
                state.error_summary = "Processing stopped at the configured iteration limit."
                break

            tool_name, tool_input = self._next_action(state, message)
            invocation = self._registry.invoke(
                tool_name, tool_input, dry_run=state.dry_run
            )
            state.iteration_count += 1
            state.traces.append(invocation.trace)

            if invocation.trace.status != ToolStatus.SUCCEEDED:
                state.status = RunStatus.FAILED
                state.error_code = invocation.trace.error_type or "TOOL_FAILED"
                state.error_summary = f"Tool '{tool_name}' did not complete successfully."
                break

            if state.stage == AgentStage.NEEDS_EXTRACTION:
                if not isinstance(invocation.output, JobOpportunity):
                    self._fail_invalid_output(state, tool_name)
                    break
                if invocation.output.message_id != state.message_id:
                    state.status = RunStatus.FAILED
                    state.error_code = "MESSAGE_ID_MISMATCH"
                    state.error_summary = (
                        "Extraction output does not belong to the source message."
                    )
                    break
                state.opportunity = invocation.output
                state.stage = AgentStage.NEEDS_EVALUATION
            elif state.stage == AgentStage.NEEDS_EVALUATION:
                if not isinstance(invocation.output, EvaluationResult):
                    self._fail_invalid_output(state, tool_name)
                    break
                state.evaluation = invocation.output
                state.stage = AgentStage.FINISHED
                state.status = RunStatus.COMPLETED

        return state

    @staticmethod
    def _next_action(state: AgentState, message: EmailMessage) -> tuple[str, object]:
        if state.stage == AgentStage.NEEDS_EXTRACTION:
            return EXTRACT_TOOL, message
        if state.stage == AgentStage.NEEDS_EVALUATION and state.opportunity is not None:
            return EVALUATE_TOOL, state.opportunity
        raise RuntimeError(f"No action is valid for stage {state.stage.value}")

    @staticmethod
    def _fail_invalid_output(state: AgentState, tool_name: str) -> None:
        state.status = RunStatus.FAILED
        state.error_code = "INVALID_TOOL_OUTPUT"
        state.error_summary = f"Tool '{tool_name}' returned an unexpected output type."
