import pytest
from hardness_plugin.tool_registry import (
    PermissionLevel,
    ToolRegistry,
    ToolSchema,
    ToolParameter,
    ToolExecutionResult,
)


class TestPermissionLevel:
    def test_level_ordering(self):
        assert PermissionLevel.READ.value < PermissionLevel.WRITE.value
        assert PermissionLevel.WRITE.value < PermissionLevel.EXECUTE.value
        assert PermissionLevel.EXECUTE.value < PermissionLevel.DEPLOY.value
        assert PermissionLevel.DEPLOY.value < PermissionLevel.ADMIN.value


class TestToolSchema:
    def test_minimal_schema(self):
        schema = ToolSchema(
            name="read_file",
            description="Read a file",
            permission_required=PermissionLevel.READ,
        )
        assert schema.name == "read_file"
        assert schema.risk_level == "low"
        assert schema.allowed_scopes == ["*"]

    def test_restricted_schema(self):
        schema = ToolSchema(
            name="deploy_prod",
            description="Deploy to production",
            permission_required=PermissionLevel.DEPLOY,
            requires_approval=True,
            risk_level="critical",
            allowed_scopes=["infra"],
            rate_limit=2,
        )
        assert schema.requires_approval is True
        assert schema.risk_level == "critical"
        assert "infra" in schema.allowed_scopes


class TestToolRegistry:
    @pytest.fixture
    def registry(self):
        return ToolRegistry(governance=None)

    @pytest.fixture
    def basic_tool(self, registry):
        async def echo(**kwargs):
            return kwargs
        registry.register(
            ToolSchema(
                name="echo",
                description="echo params",
                permission_required=PermissionLevel.READ,
            ),
            echo,
        )
        return registry

    def test_register_tool(self, registry):
        async def impl(**kwargs):
            return {"ok": True}
        registry.register(
            ToolSchema(
                name="test_tool",
                description="A test tool",
                permission_required=PermissionLevel.WRITE,
            ),
            impl,
        )
        assert "test_tool" in registry.tools

    def test_register_duplicate_raises(self, basic_tool):
        with pytest.raises(ValueError, match="already registered"):
            async def impl(**kwargs):
                pass
            basic_tool.register(
                ToolSchema(
                    name="echo",
                    description="dup",
                    permission_required=PermissionLevel.READ,
                ),
                impl,
            )

    def test_unregister_tool(self, basic_tool):
        basic_tool.unregister("echo")
        assert "echo" not in basic_tool.tools

    def test_unregister_unknown_raises(self, registry):
        with pytest.raises(ValueError, match="not registered"):
            registry.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, registry):
        result = await registry.call(
            "nonexistent",
            PermissionLevel.READ,
            {},
            "session-1",
        )
        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_call_permission_denied(self, basic_tool):
        # Register a WRITE-level tool
        async def write_impl(**kwargs):
            return {"written": True}
        basic_tool.register(
            ToolSchema(
                name="write_file",
                description="write a file",
                permission_required=PermissionLevel.WRITE,
            ),
            write_impl,
        )
        result = await basic_tool.call(
            "write_file",
            PermissionLevel.READ,  # insufficient
            {"path": "/tmp/x"},
            "session-2",
        )
        assert result.success is False
        assert "requires WRITE" in result.error

    @pytest.mark.asyncio
    async def test_call_success(self, basic_tool):
        result = await basic_tool.call(
            "echo",
            PermissionLevel.READ,
            {"message": "hello"},
            "session-3",
        )
        assert result.success is True
        assert result.output == {"message": "hello"}

    @pytest.mark.asyncio
    async def test_call_scope_restriction(self, registry):
        async def impl(**kwargs):
            return {"done": True}
        registry.register(
            ToolSchema(
                name="deploy",
                description="deploy",
                permission_required=PermissionLevel.DEPLOY,
                allowed_scopes=["infra"],
            ),
            impl,
        )
        result = await registry.call(
            "deploy",
            PermissionLevel.DEPLOY,
            {},
            "session-4",
            task_scope="api",
        )
        assert result.success is False
        assert "not allowed for scope" in result.error

    def test_rate_limiting(self, registry):
        async def impl(**kwargs):
            return {"ok": True}
        registry.register(
            ToolSchema(
                name="rate_limited",
                description="rate limited tool",
                permission_required=PermissionLevel.READ,
                rate_limit=2,
            ),
            impl,
        )
        assert registry._check_rate_limit("rate_limited", 2) is True
        assert registry._check_rate_limit("rate_limited", 2) is True
        assert registry._check_rate_limit("rate_limited", 2) is False
