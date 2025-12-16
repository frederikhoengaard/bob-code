from src.tools.base import BaseTool


class EnterPlanModeTool(BaseTool):
    """Tool for entering plan mode to thoroughly explore and plan complex tasks"""

    def __init__(self, on_enter_plan_mode_callback=None):
        """
        Initialize EnterPlanModeTool.

        Args:
            on_enter_plan_mode_callback: Async callback function() -> bool
                                        Should request user approval and return True/False
        """
        self.on_enter_plan_mode_callback = on_enter_plan_mode_callback

    @property
    def name(self) -> str:
        return "enter_plan_mode"

    @property
    def description(self) -> str:
        return """Use this tool when you encounter a complex task that requires careful planning and exploration before implementation. This tool transitions you into plan mode where you can thoroughly explore the codebase and design an implementation approach.

## When to Use This Tool

Use EnterPlanMode when ANY of these conditions apply:

1. **Multiple Valid Approaches**: The task can be solved in several different ways, each with trade-offs
   - Example: "Add caching to the API" - could use Redis, in-memory, file-based, etc.
   - Example: "Improve performance" - many optimization strategies possible

2. **Significant Architectural Decisions**: The task requires choosing between architectural patterns
   - Example: "Add real-time updates" - WebSockets vs SSE vs polling
   - Example: "Implement state management" - Redux vs Context vs custom solution

3. **Large-Scale Changes**: The task touches many files or systems
   - Example: "Refactor the authentication system"
   - Example: "Migrate from REST to GraphQL"

4. **Unclear Requirements**: You need to explore before understanding the full scope
   - Example: "Make the app faster" - need to profile and identify bottlenecks
   - Example: "Fix the bug in checkout" - need to investigate root cause

5. **User Input Needed**: You'll need to ask clarifying questions before starting
   - If you would use AskUserQuestion to clarify the approach, consider EnterPlanMode instead
   - Plan mode lets you explore first, then present options with context

## When NOT to Use This Tool

Do NOT use EnterPlanMode for:
- Simple, straightforward tasks with obvious implementation
- Small bug fixes where the solution is clear
- Adding a single function or small feature
- Tasks you're already confident how to implement
- Research-only tasks (use the Task tool with explore agent instead)

## What Happens in Plan Mode

In plan mode, you'll:
1. Thoroughly explore the codebase using Glob, Grep, and Read tools
2. Understand existing patterns and architecture
3. Design an implementation approach
4. Present your plan to the user for approval
5. Use AskUserQuestion if you need to clarify approaches
6. Exit plan mode with ExitPlanMode when ready to implement

## Examples

### GOOD - Use EnterPlanMode:
User: "Add user authentication to the app"
- This requires architectural decisions (session vs JWT, where to store tokens, middleware structure)

User: "Optimize the database queries"
- Multiple approaches possible, need to profile first, significant impact

User: "Implement dark mode"
- Architectural decision on theme system, affects many components

### BAD - Don't use EnterPlanMode:
User: "Fix the typo in the README"
- Straightforward, no planning needed

User: "Add a console.log to debug this function"
- Simple, obvious implementation

User: "What files handle routing?"
- Research task, not implementation planning

## Important Notes

- This tool REQUIRES user approval - they must consent to entering plan mode
- Be thoughtful about when to use it - unnecessary plan mode slows down simple tasks
- If unsure whether to use it, err on the side of starting implementation
- You can always ask the user "Would you like me to plan this out first?"
"""

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
        # No permission required - entering plan mode is a workflow state change
        return None

    async def execute(self) -> str:
        """
        Request to enter plan mode.

        Returns:
            Message indicating whether plan mode was entered or denied
        """
        # Check if callback is available
        if not self.on_enter_plan_mode_callback:
            return "Error: EnterPlanMode tool not properly initialized (no callback provided)"

        try:
            # Call the callback to request user approval for plan mode
            approved = await self.on_enter_plan_mode_callback()

            if approved:
                return (
                    "Plan mode activated. You are now in planning mode.\n\n"
                    "Next steps:\n"
                    "1. Explore the codebase thoroughly using read, glob, grep, and bash tools\n"
                    "2. Understand existing patterns and architecture\n"
                    "3. Design your implementation approach\n"
                    "4. Use ask_user_question if you need clarification on approaches\n"
                    "5. When ready, present your plan and wait for user approval\n"
                    "6. Use exit_plan_mode when planning is complete and you're ready to implement"
                )
            else:
                return (
                    "Plan mode request denied by user. Proceeding with direct implementation.\n"
                    "Continue with the task without entering plan mode."
                )

        except Exception as e:
            return f"Error requesting plan mode: {str(e)}"
