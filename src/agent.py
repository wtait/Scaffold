import json
import os
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.types import CallToolResult, Tool


from beam import Image, PythonVersion, realtime

from baml_client.sync_client import BamlSyncClient, b
from baml_client.types import Message as ConvoMessage

from .client import mcp_session


class MessageType(Enum):
    INIT = "init"
    USER = "user"
    AGENT_PARTIAL = "agent_partial"
    AGENT_FINAL = "agent_final"
    LOAD_CODE = "load_code"
    EDIT_CODE = "edit_code"
    UPDATE_IN_PROGRESS = "update_in_progress"
    UPDATE_FILE = "update_file"
    UPDATE_COMPLETED = "update_completed"


@dataclass
class Message:
    id: str
    timestamp: int
    type: MessageType
    data: dict

    @classmethod
    def new(cls, type: MessageType, data: dict, id: str | None = None) -> "Message":
        return cls(
            type=type,
            data=data,
            id=id or str(uuid.uuid4()),
            timestamp=time.time_ns() // 1_000_000,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class ToolType(Enum):
    CREATE_APP_ENVIRONMENT = "create_app_environment"
    LOAD_CODE = "load_code"
    EDIT_CODE = "edit_code"


class Agent:
    def __init__(self, *, mcp_url: str):
        self.model_client: BamlSyncClient = b
        self.mcp_url: str = mcp_url
        self.tools: list[Tool] = []
        self.init_data: dict = {}
        self.history: list[dict] = []

    async def init(self):
        await self.load_tools()
        await self.create_app_environment()

    async def load_tools(self):
        async with mcp_session(self.mcp_url) as session:
            self.tools = await session.list_tools()

    async def create_app_environment(self):
        async with mcp_session(self.mcp_url) as session:
            response: CallToolResult = await session.call_tool(
                name=ToolType.CREATE_APP_ENVIRONMENT.value,
                arguments={},
            )
            self.init_data = json.loads(response.content[0].text)

    async def load_code(self, sandbox_id: str):
        async with mcp_session(self.mcp_url) as session:
            response: CallToolResult = await session.call_tool(
                name=ToolType.LOAD_CODE.value,
                arguments={"sandbox_id": sandbox_id},
            )
            return json.loads(response.content[0].text)

    async def edit_code(self, sandbox_id: str, code_map: dict):
        async with mcp_session(self.mcp_url) as session:
            response: CallToolResult = await session.call_tool(
                name=ToolType.EDIT_CODE.value,
                arguments={
                    "sandbox_id": sandbox_id,
                    "code_map": code_map,
                },
            )
            return json.loads(response.content[0].text)

    async def add_to_history(self, user_feedback: str, agent_plan: str):
        self.history.append(
            {
                "role": "user",
                "content": user_feedback,
            }
        )

        self.history.append(
            {
                "role": "assistant",
                "content": agent_plan,
            }
        )

    def get_history(self):
        return [
            ConvoMessage(role=msg["role"], content=msg["content"])
            for msg in self.history
        ]

    async def send_feedback(self, feedback: str):
        yield Message.new(MessageType.UPDATE_IN_PROGRESS, {}).to_dict()

        code_map, package_json = await self.load_code(self.init_data["sandbox_id"])

        code_files = []
        for path, content in code_map.items():
            code_files.append({"path": path, "content": content})

        history = self.get_history()
        stream = self.model_client.stream.EditCode(
            history, feedback, code_files, package_json
        )
        sent_plan = False

        new_code_map = {}
        plan_msg_id = str(uuid.uuid4())
        file_msg_id = str(uuid.uuid4())

        for partial in stream:
            if partial.plan.state != "Complete" and not sent_plan:
                yield Message.new(
                    MessageType.AGENT_PARTIAL,
                    {"text": partial.plan.value},
                    id=plan_msg_id,
                ).to_dict()

            if partial.plan.state == "Complete" and not sent_plan:
                yield Message.new(
                    MessageType.AGENT_FINAL,
                    {"text": partial.plan.value},
                    id=plan_msg_id,
                ).to_dict()

                await self.add_to_history(feedback, partial.plan.value)

                sent_plan = True

            for file in partial.files:
                if file.path not in new_code_map:
                    yield Message.new(
                        MessageType.UPDATE_FILE,
                        {"text": f"Working on {file.path}"},
                        id=file_msg_id,
                    ).to_dict()

                    new_code_map[file.path] = file.content

        await self.edit_code(self.init_data["sandbox_id"], new_code_map)

        yield Message.new(MessageType.UPDATE_COMPLETED, {}).to_dict()


async def _load_agent():
    agent = Agent(mcp_url=os.getenv("LOVABLE_MCP_URL"))
    print("Loaded agent")
    return agent


@realtime(
    cpu=1.0,
    memory=1024,
    on_start=_load_agent,
    image=Image(
        python_packages="requirements.txt", python_version=PythonVersion.Python312
    ),
    secrets=["OPENAI_API_KEY", "LOVABLE_MCP_URL"],
    concurrent_requests=1000,
    keep_warm_seconds=300,
)
async def handler(event, context):
    agent: Agent = context.on_start_value
    msg = json.loads(event)

    match msg.get("type"):
        case MessageType.USER.value:
            return agent.send_feedback(msg["data"]["text"])
        case MessageType.INIT.value:
            await agent.init()
            return Message.new(MessageType.INIT, agent.init_data).to_dict()
        case MessageType.LOAD_CODE.value:
            code_map = await agent.load_code(msg["data"]["sandbox_id"])
            return Message.new(MessageType.LOAD_CODE, code_map).to_dict()
        case _:
            return {}
