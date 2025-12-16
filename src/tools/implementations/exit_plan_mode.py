from src.tools.base import BaseTool


class ExitPlanModeTool(BaseTool):
    """Tool for exiting plan mode and transitioning to implementation"""

    def __init__(self, on_exit_plan_mode_callback=None):
        """
        Initialize ExitPlanModeTool.

        Args:
            on_exit_plan_mode_callback: Async callback function() -> str
                                       Should handle the transition out of plan mode
        """
        self.on_exit_plan_mode_callback = on_exit_plan_mode_callback

    @property
    def name(self) -> str:
        return "exit_plan_mode"

    @property
    def description(self) -> str:
        return """Use this tool when you are in plan mode and have finished planning and are ready for user approval.

## How This Tool Works
- You should have already presented your implementation plan in the conversation
- This tool signals that you're done planning and ready to transition to implementation
- The tool will exit plan mode and allow you to begin implementing

## When to Use This Tool
IMPORTANT: Only use this tool when the task requires planning the implementation steps of a task that requires writing code. For research tasks where you're gathering information, searching files, reading files or in general trying to understand the codebase - do NOT use this tool.

## Handling Ambiguity in Plans
Before using this tool, ensure your plan is clear and unambiguous. If there are multiple valid approaches or unclear requirements:
1. Use the ask_user_question tool to clarify with the user
2. Ask about specific implementation choices (e.g., architectural patterns, which library to use)
3. Clarify any assumptions that could affect the implementation
4. Update your plan based on user feedback
5. Only proceed with exit_plan_mode after resolving ambiguities and updating the plan

## Workflow
This tool should be called after:
1. You've thoroughly explored the codebase
2. You've designed an implementation approach
3. You've presented your plan to the user in the conversation
4. You've clarified any ambiguities with ask_user_question
5. You're ready to start implementing

## Examples

1. Initial task: "Search for and understand the implementation of vim mode in the codebase" - Do not use the exit plan mode tool because you are not planning the implementation steps of a task.
2. Initial task: "Help me implement yank mode for vim" - Use the exit plan mode tool after you have finished planning the implementation steps of the task.
3. Initial task: "Add a new feature to handle user authentication" - If unsure about auth method (OAuth, JWT, etc.), use ask_user_question first, then use exit plan mode tool after clarifying the approach."""

    @property
    def parameters_schema(self) -> dict:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    @property
    def required_permission(self) -> str | None:
        # No permission required - exiting plan mode is a workflow state change
        return None

    async def execute(self) -> str:
        """
        Exit plan mode and transition to implementation.

        Returns:
            Message indicating plan mode has been exited
        """
        # Check if callback is available
        if not self.on_exit_plan_mode_callback:
            return "Error: ExitPlanMode tool not properly initialized (no callback provided)"

        try:
            # Call the callback to handle exiting plan mode
            result = await self.on_exit_plan_mode_callback()
            return result

        except Exception as e:
            return f"Error exiting plan mode: {str(e)}"
