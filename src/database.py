import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, List
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/lovable_clone"
)

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ProjectSession(Base):
    """Model for storing project session data"""
    __tablename__ = "project_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, unique=True, index=True, nullable=False)
    sandbox_id = Column(String, nullable=True)
    sandbox_url = Column(String, nullable=True)
    status = Column(String, default="created")  # created, active, completed, error
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    meta_data = Column(JSON, default={})

class ConversationHistory(Base):
    """Model for storing conversation history"""
    __tablename__ = "conversation_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, index=True, nullable=False)
    message_id = Column(String, nullable=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=True)  # INIT, USER, AGENT_PARTIAL, etc.
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    meta_data = Column(JSON, default={})

class ProjectFile(Base):
    """Model for storing project file versions"""
    __tablename__ = "project_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    meta_data = Column(JSON, default={})

class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self, db_url: str = None):
        if db_url:
            self.engine = create_engine(db_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        else:
            self.engine = engine
            self.SessionLocal = SessionLocal
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def create_project_session(self, session_id: str, metadata: Dict = None) -> ProjectSession:
        """Create a new project session"""
        with self.get_session() as db:
            project_session = ProjectSession(
                session_id=session_id,
                meta_data=metadata or {}
            )
            db.add(project_session)
            db.commit()
            db.refresh(project_session)
            return project_session
    
    def get_project_session(self, session_id: str) -> Optional[ProjectSession]:
        """Get project session by session_id"""
        with self.get_session() as db:
            return db.query(ProjectSession).filter(ProjectSession.session_id == session_id).first()
    
    def update_project_session(self, session_id: str, **kwargs) -> Optional[ProjectSession]:
        """Update project session"""
        with self.get_session() as db:
            project_session = db.query(ProjectSession).filter(ProjectSession.session_id == session_id).first()
            if project_session:
                for key, value in kwargs.items():
                    setattr(project_session, key, value)
                project_session.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(project_session)
            return project_session
    
    def add_conversation_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        message_id: str = None,
        message_type: str = None,
        metadata: Dict = None
    ) -> ConversationHistory:
        """Add a message to conversation history"""
        with self.get_session() as db:
            message = ConversationHistory(
                session_id=session_id,
                message_id=message_id,
                role=role,
                content=content,
                message_type=message_type,
                meta_data=metadata or {}
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
    
    def get_conversation_history(self, session_id: str, limit: int = 100) -> List[ConversationHistory]:
        """Get conversation history for a session"""
        with self.get_session() as db:
            return db.query(ConversationHistory)\
                .filter(ConversationHistory.session_id == session_id)\
                .order_by(ConversationHistory.timestamp.desc())\
                .limit(limit)\
                .all()
    
    def save_project_file(
        self, 
        session_id: str, 
        file_path: str, 
        content: str,
        meta_data: Dict = None
    ) -> ProjectFile:
        """Save a project file version"""
        with self.get_session() as db:
            # Get current version number
            latest = db.query(ProjectFile)\
                .filter(ProjectFile.session_id == session_id, ProjectFile.file_path == file_path)\
                .order_by(ProjectFile.version.desc())\
                .first()
            
            version = (latest.version + 1) if latest else 1
            
            project_file = ProjectFile(
                session_id=session_id,
                file_path=file_path,
                content=content,
                version=version,
                meta_data=meta_data or {}
            )
            db.add(project_file)
            db.commit()
            db.refresh(project_file)
            return project_file
    
    def get_project_files(self, session_id: str, latest_only: bool = True) -> List[ProjectFile]:
        """Get project files for a session"""
        with self.get_session() as db:
            if latest_only:
                # Get only the latest version of each file
                from sqlalchemy import func
                subquery = db.query(
                    ProjectFile.file_path,
                    func.max(ProjectFile.version).label('max_version')
                ).filter(ProjectFile.session_id == session_id)\
                 .group_by(ProjectFile.file_path)\
                 .subquery()
                
                return db.query(ProjectFile)\
                    .join(subquery, 
                          (ProjectFile.file_path == subquery.c.file_path) & 
                          (ProjectFile.version == subquery.c.max_version))\
                    .filter(ProjectFile.session_id == session_id)\
                    .all()
            else:
                return db.query(ProjectFile)\
                    .filter(ProjectFile.session_id == session_id)\
                    .order_by(ProjectFile.file_path, ProjectFile.version)\
                    .all()
    
    def get_project_file(self, session_id: str, file_path: str, version: int = None) -> Optional[ProjectFile]:
        """Get a specific project file"""
        with self.get_session() as db:
            query = db.query(ProjectFile)\
                .filter(ProjectFile.session_id == session_id, ProjectFile.file_path == file_path)
            
            if version:
                query = query.filter(ProjectFile.version == version)
            else:
                query = query.order_by(ProjectFile.version.desc())
            
            return query.first()
    
    def cleanup_session(self, session_id: str) -> bool:
        """Clean up all data for a session"""
        with self.get_session() as db:
            try:
                # Delete in order due to potential foreign key constraints
                db.query(ConversationHistory).filter(ConversationHistory.session_id == session_id).delete()
                db.query(ProjectFile).filter(ProjectFile.session_id == session_id).delete()
                db.query(ProjectSession).filter(ProjectSession.session_id == session_id).delete()
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                raise e

# Global database manager instance
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return db_manager

def init_database():
    """Initialize the database (create tables)"""
    db_manager.create_tables()