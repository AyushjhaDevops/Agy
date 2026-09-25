from app.tools.base import ToolSpec


def tool_catalog() -> list[ToolSpec]:
    from app.tools.filesystem import FileReadTool, FileSearchTool, PatchTool
    from app.tools.terminal import GitDiffTool, TerminalTool, TestTool
    return [item.spec for item in (FileReadTool, FileSearchTool, PatchTool, TerminalTool, GitDiffTool, TestTool)]
