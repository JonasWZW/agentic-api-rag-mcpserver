"""MCP prompts definitions."""


def get_prompt_definitions() -> list[dict]:
    """Get MCP prompt definitions."""
    return [
        {
            "name": "analyze_api",
            "description": "Analyze an API's purpose and usage",
            "arguments": [
                {
                    "name": "api_id",
                    "description": "API unique identifier",
                    "required": True,
                }
            ],
        },
        {
            "name": "generate_request",
            "description": "Generate request code example for an API",
            "arguments": [
                {
                    "name": "api_id",
                    "description": "API unique identifier",
                    "required": True,
                },
                {
                    "name": "language",
                    "description": "Programming language (python, javascript, curl)",
                    "required": False,
                    "default": "python",
                },
            ],
        },
    ]


class MCPPrompts:
    """MCP prompts provider."""

    def __init__(self, simple_manager=None):
        """Initialize MCP prompts."""
        self.simple_manager = simple_manager

    async def analyze_api(self, api_id: str) -> str:
        """Analyze API purpose."""
        if not self.simple_manager:
            return "RAG engine not configured"

        # Get API details
        doc = self.simple_manager.retriever.get_api_by_id(api_id)
        if not doc:
            return f"API not found: {api_id}"

        # Get context from graph
        context = {}
        if self.simple_manager.kg:
            context = self.simple_manager.kg.get_api_context(api_id)

        # Build analysis
        analysis = f"# API 分析: {api_id}\n\n"

        api_info = context.get("api", {})
        analysis += f"## 基本信息\n"
        analysis += f"- 方法: {api_info.get('method', '?').upper()}\n"
        analysis += f"- 路径: {api_info.get('path', '')}\n"
        analysis += f"- 摘要: {api_info.get('summary', '')}\n\n"

        if context.get("dependencies"):
            analysis += f"## 依赖的 API\n"
            for dep in context["dependencies"]:
                analysis += f"- {dep}\n"
            analysis += "\n"

        if context.get("related_apis"):
            analysis += f"## 相关 API\n"
            for related in context["related_apis"][:5]:
                analysis += f"- {related}\n"
            analysis += "\n"

        return analysis

    async def generate_request(self, api_id: str, language: str = "python") -> str:
        """Generate request code example."""
        if not self.simple_manager:
            return "RAG engine not configured"

        # Get API details
        doc = self.simple_manager.retriever.get_api_by_id(api_id)
        if not doc:
            return f"API not found: {api_id}"

        api_info = dict(doc.metadata)
        method = api_info.get("method", "GET").upper()
        path = api_info.get("path", "")

        if language == "python":
            code = f'''import requests

response = requests.{method.lower()}(
    "{path}",
    headers={{
        "Authorization": "Bearer <your_token>",
        "Content-Type": "application/json"
    }}
)

# For async:
# import httpx
# async with httpx.AsyncClient() as client:
#     response = await client.{method.lower()}("{path}", ...)
'''
        elif language == "javascript":
            code = f'''// Using fetch
const response = await fetch("{path}", {{
    method: "{method}",
    headers: {{
        "Authorization": "Bearer <your_token>",
        "Content-Type": "application/json"
    }}
}});

const data = await response.json();
'''
        elif language == "curl":
            code = f'''curl -X {method} "{path}" \\
  -H "Authorization: Bearer <your_token>" \\
  -H "Content-Type: application/json"
'''
        else:
            code = f"# Unsupported language: {language}"

        return f"# {api_id}\n\n{code}"
