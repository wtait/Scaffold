import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum
import logging

from baml_client.sync_client import BamlSyncClient, b
from baml_client.types import Message as ConvoMessage

from .tools import SandboxTools
from .database import get_db_manager
from .storage import get_storage_manager

logger = logging.getLogger(__name__)


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
    session_id: str

    @classmethod
    def new(
        cls,
        type: MessageType,
        data: dict,
        id: str | None = None,
        session_id: str | None = None,
    ) -> "Message":
        return cls(
            type=type,
            data=data,
            id=id or str(uuid.uuid4()),
            timestamp=time.time_ns() // 1_000_000,
            session_id=session_id or str(uuid.uuid4()),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


class Agent:
    def __init__(self):
        self.model_client: BamlSyncClient = b
        self.session_data: dict = {}  # map of session -> session_data
        self.history: list[dict] = []
        self.db_manager = get_db_manager()
        self.storage_manager = get_storage_manager()
        self.sandbox_tools = SandboxTools()

    async def init(self, session_id: str) -> bool:
        exists = await self.create_app_environment(session_id)
        
        # Create or get database session
        db_session = self.db_manager.get_project_session(session_id)
        if not db_session:
            self.db_manager.create_project_session(
                session_id=session_id,
                metadata={"initialized_at": time.time()}
            )
        
        return exists

    async def create_app_environment(self, session_id: str):
        if session_id not in self.session_data:
            # Check if session already exists in database
            db_session = self.db_manager.get_project_session(session_id)
            
            if db_session and db_session.sandbox_id:
                # Try to reuse existing sandbox
                try:
                    sandbox_data = await self.sandbox_tools.connect_existing_sandbox(
                        session_id, db_session.sandbox_id, db_session.sandbox_url
                    )
                    self.session_data[session_id] = sandbox_data
                    logger.info(f"Reconnected to existing sandbox for session {session_id}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to reconnect to existing sandbox, creating new one: {e}")
            
            # Create new sandbox
            try:
                sandbox_data = await self.sandbox_tools.create_app_environment(session_id)
                self.session_data[session_id] = sandbox_data
                
                # Update database with sandbox info
                self.db_manager.update_project_session(
                    session_id=session_id,
                    sandbox_id=sandbox_data.get("sandbox_id"),
                    sandbox_url=sandbox_data.get("url"),
                    status="active"
                )
                
                logger.info(f"Created new sandbox for session {session_id}")
                return False
            except Exception as e:
                logger.error(f"Failed to create sandbox for session {session_id}: {e}")
                raise

        return True

    async def load_code(self, *, session_id: str):
        if session_id not in self.session_data:
            raise ValueError(f"No sandbox found for session {session_id}")
        
        sandbox_id = self.session_data[session_id]["sandbox_id"]
        return await self.sandbox_tools.load_code(sandbox_id)

    async def edit_code(self, *, session_id: str, code_map: dict):
        if session_id not in self.session_data:
            raise ValueError(f"No sandbox found for session {session_id}")
        
        sandbox_id = self.session_data[session_id]["sandbox_id"]
        result = await self.sandbox_tools.edit_code(sandbox_id, code_map)
        
        # Save files to database for versioning
        for file_path, content in code_map.items():
            self.db_manager.save_project_file(
                session_id=session_id,
                file_path=file_path,
                content=content,
                meta_data={"updated_at": time.time()}
            )
        
        return result

    async def add_to_history(self, user_feedback: str, agent_plan: str, session_id: str = None):
        user_msg = {
            "role": "user",
            "content": user_feedback,
        }
        assistant_msg = {
            "role": "assistant",
            "content": agent_plan,
        }
        
        self.history.append(user_msg)
        self.history.append(assistant_msg)
        
        # Save to database if session_id provided
        if session_id:
            self.db_manager.add_conversation_message(
                session_id=session_id,
                role="user",
                content=user_feedback,
                message_type="USER"
            )
            self.db_manager.add_conversation_message(
                session_id=session_id,
                role="assistant",
                content=agent_plan,
                message_type="AGENT_FINAL"
            )

    def get_history(self):
        return [
            ConvoMessage(role=msg["role"], content=msg["content"])
            for msg in self.history
        ]

    async def send_feedback(self, *, session_id: str, feedback: str):
        yield Message.new(MessageType.UPDATE_IN_PROGRESS, {}).to_dict()

        code_map, package_json = await self.load_code(session_id=session_id)

        code_files = []
        for path, content in code_map.items():
            code_files.append({"path": path, "content": str(content)})

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
                    session_id=session_id,
                ).to_dict()

            if partial.plan.state == "Complete" and not sent_plan:
                yield Message.new(
                    MessageType.AGENT_FINAL,
                    {"text": partial.plan.value},
                    id=plan_msg_id,
                    session_id=session_id,
                ).to_dict()

                await self.add_to_history(feedback, partial.plan.value, session_id)

                sent_plan = True

            for file in partial.files:
                if file.path not in new_code_map:
                    yield Message.new(
                        MessageType.UPDATE_FILE,
                        {"text": f"Working on {file.path}"},
                        id=file_msg_id,
                        session_id=session_id,
                    ).to_dict()

                    new_code_map[file.path] = file.content

        await self.edit_code(session_id=session_id, code_map=new_code_map)

        yield Message.new(
            MessageType.UPDATE_COMPLETED, {}, session_id=session_id
        ).to_dict()


# The agent is now used by the websocket_server.py for real-time communication
