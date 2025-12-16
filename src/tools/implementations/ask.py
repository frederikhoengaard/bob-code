from typing import Any

from src.tools.base import BaseTool


class Question:
    """Represents a single question to ask the user"""

    def __init__(
        self,
        question: str,
        header: str,
        options: list[dict[str, str]],
        multi_select: bool = False,
    ):
        """
        Args:
            question: The question text to display
            header: Short label for the question (max 12 chars)
            options: List of dicts with 'label' and 'description' keys
            multi_select: Whether to allow multiple selections
        """
        self.question = question
        self.header = header
        self.options = options
        self.multi_select = multi_select


class AskUserQuestionTool(BaseTool):
    """Tool for asking users questions during execution"""

    def __init__(self, on_question_callback=None):
        """
        Initialize AskUserQuestionTool.

        Args:
            on_question_callback: Async callback function(questions) -> dict of answers
                                 The callback should display questions to user and return answers
        """
        self.on_question_callback = on_question_callback

    @property
    def name(self) -> str:
        return "ask_user_question"

    @property
    def description(self) -> str:
        return """Use this tool when you need to ask the user questions during execution. This allows you to:
1. Gather user preferences or requirements
2. Clarify ambiguous instructions
3. Get decisions on implementation choices as you work
4. Offer choices to the user about what direction to take.

Usage notes:
- Users will always be able to select "Other" to provide custom text input
- Use multiSelect: true to allow multiple answers to be selected for a question
- Each question should have 2-4 options
- Ask 1-4 questions at a time
- Keep question text clear and specific"""

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "description": "Questions to ask the user (1-4 questions)",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The complete question to ask the user. Should be clear, specific, and end with a question mark. Example: 'Which library should we use for date formatting?' If multiSelect is true, phrase it accordingly, e.g. 'Which features do you want to enable?'",
                            },
                            "header": {
                                "type": "string",
                                "description": "Very short label displayed as a chip/tag (max 12 chars). Examples: 'Auth method', 'Library', 'Approach'.",
                            },
                            "options": {
                                "type": "array",
                                "description": "The available choices for this question. Must have 2-4 options. Each option should be a distinct, mutually exclusive choice (unless multiSelect is enabled). There should be no 'Other' option, that will be provided automatically.",
                                "minItems": 2,
                                "maxItems": 4,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {
                                            "type": "string",
                                            "description": "The display text for this option that the user will see and select. Should be concise (1-5 words) and clearly describe the choice.",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Explanation of what this option means or what will happen if chosen. Useful for providing context about trade-offs or implications.",
                                        },
                                    },
                                    "required": ["label", "description"],
                                },
                            },
                            "multiSelect": {
                                "type": "boolean",
                                "description": "Set to true to allow the user to select multiple options instead of just one. Use when choices are not mutually exclusive.",
                            },
                        },
                        "required": ["question", "header", "options", "multiSelect"],
                    },
                },
            },
            "required": ["questions"],
        }

    @property
    def required_permission(self) -> str | None:
        # No permission required - asking questions is always allowed
        return None

    async def execute(self, questions: list[dict[str, Any]]) -> str:
        """
        Ask user questions and return their answers.

        Args:
            questions: List of question dictionaries with:
                - question: str - The question text
                - header: str - Short label (max 12 chars)
                - options: list[dict] - Options with 'label' and 'description'
                - multiSelect: bool - Allow multiple selections

        Returns:
            Formatted string with user's answers
        """
        # Validate questions
        if not questions or len(questions) > 4:
            return "Error: Must provide 1-4 questions"

        # Parse questions
        parsed_questions = []
        for i, q in enumerate(questions):
            try:
                question_text = q.get("question")
                header = q.get("header")
                options = q.get("options", [])
                multi_select = q.get("multiSelect", False)

                # Validate
                if not question_text or not header:
                    return f"Error: Question {i+1} missing 'question' or 'header' field"

                if len(header) > 12:
                    return f"Error: Question {i+1} header '{header}' exceeds 12 characters"

                if not options or len(options) < 2 or len(options) > 4:
                    return f"Error: Question {i+1} must have 2-4 options, got {len(options)}"

                # Validate options
                for j, opt in enumerate(options):
                    if "label" not in opt or "description" not in opt:
                        return (
                            f"Error: Question {i+1}, option {j+1} missing 'label' or 'description'"
                        )

                parsed_questions.append(
                    Question(
                        question=question_text,
                        header=header,
                        options=options,
                        multi_select=multi_select,
                    )
                )
            except Exception as e:
                return f"Error parsing question {i+1}: {str(e)}"

        # Check if callback is available
        if not self.on_question_callback:
            return "Error: Question tool not properly initialized (no callback provided)"

        try:
            # Call the callback to display questions and get answers
            answers = await self.on_question_callback(parsed_questions)

            # Format the response
            if not answers:
                return "Error: No answers received from user"

            # Build response string
            response_parts = ["User's answers:"]
            for i, question in enumerate(parsed_questions):
                answer_key = f"question_{i}"
                answer = answers.get(answer_key, "No answer provided")

                response_parts.append(f"\n{question.header}: {answer}")

            return "\n".join(response_parts)

        except Exception as e:
            return f"Error asking questions: {str(e)}"
