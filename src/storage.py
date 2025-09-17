import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class StorageManager(ABC):
    """Abstract storage manager interface"""
    
    @abstractmethod
    async def save_project(self, session_id: str, files: Dict[str, str], metadata: Dict = None) -> str:
        """Save project files and return project ID"""
        pass
    
    @abstractmethod
    async def load_project(self, project_id: str) -> Tuple[Dict[str, str], Dict]:
        """Load project files and metadata"""
        pass
    
    @abstractmethod
    async def list_projects(self, limit: int = 100) -> List[Dict]:
        """List all projects"""
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        pass
    
    @abstractmethod
    async def export_project(self, project_id: str, format: str = "zip") -> bytes:
        """Export project as zip or tar"""
        pass

class LocalStorageManager(StorageManager):
    """Local filesystem storage implementation"""
    
    def __init__(self, storage_path: str = "./projects"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        logger.info(f"Using local storage at: {self.storage_path}")
    
    def _get_project_dir(self, project_id: str) -> Path:
        return self.storage_path / project_id
    
    async def save_project(self, session_id: str, files: Dict[str, str], metadata: Dict = None) -> str:
        """Save project to local filesystem"""
        project_id = f"project_{session_id}_{int(datetime.now().timestamp())}"
        project_dir = self._get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save files
            for file_path, content in files.items():
                # Remove leading slash and convert to relative path
                rel_path = file_path.lstrip('/')
                full_path = project_dir / rel_path
                
                # Create parent directories
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Save metadata
            metadata = metadata or {}
            metadata.update({
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'file_count': len(files)
            })
            
            with open(project_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved project {project_id} with {len(files)} files")
            return project_id
            
        except Exception as e:
            logger.error(f"Failed to save project {project_id}: {e}")
            # Clean up on failure
            if project_dir.exists():
                shutil.rmtree(project_dir)
            raise
    
    async def load_project(self, project_id: str) -> Tuple[Dict[str, str], Dict]:
        """Load project from local filesystem"""
        project_dir = self._get_project_dir(project_id)
        
        if not project_dir.exists():
            raise FileNotFoundError(f"Project {project_id} not found")
        
        files = {}
        metadata = {}
        
        # Load metadata
        metadata_file = project_dir / 'metadata.json'
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        # Load files
        for file_path in project_dir.rglob('*'):
            if file_path.is_file() and file_path.name != 'metadata.json':
                rel_path = file_path.relative_to(project_dir)
                with open(file_path, 'r', encoding='utf-8') as f:
                    files[str(rel_path)] = f.read()
        
        logger.info(f"Loaded project {project_id} with {len(files)} files")
        return files, metadata
    
    async def list_projects(self, limit: int = 100) -> List[Dict]:
        """List projects in local storage"""
        projects = []
        
        for project_dir in self.storage_path.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        projects.append({
                            'project_id': project_dir.name,
                            'session_id': metadata.get('session_id'),
                            'created_at': metadata.get('created_at'),
                            'file_count': metadata.get('file_count', 0),
                            'size': sum(f.stat().st_size for f in project_dir.rglob('*') if f.is_file())
                        })
                        
                        if len(projects) >= limit:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for {project_dir.name}: {e}")
        
        return sorted(projects, key=lambda x: x.get('created_at', ''), reverse=True)
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete project from local storage"""
        project_dir = self._get_project_dir(project_id)
        
        if project_dir.exists():
            try:
                shutil.rmtree(project_dir)
                logger.info(f"Deleted project {project_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete project {project_id}: {e}")
                return False
        
        return False
    
    async def export_project(self, project_id: str, format: str = "zip") -> bytes:
        """Export project as zip file"""
        project_dir = self._get_project_dir(project_id)
        
        if not project_dir.exists():
            raise FileNotFoundError(f"Project {project_id} not found")
        
        if format.lower() == "zip":
            import zipfile
            
            with tempfile.BytesIO() as buffer:
                with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in project_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(project_dir)
                            zip_file.write(file_path, arcname)
                
                return buffer.getvalue()
        else:
            raise NotImplementedError(f"Export format '{format}' not supported")

class S3StorageManager(StorageManager):
    """S3-compatible storage implementation"""
    
    def __init__(self, bucket_name: str, access_key: str = None, secret_key: str = None, endpoint_url: str = None):
        self.bucket_name = bucket_name
        
        # Use environment variables if not provided
        access_key = access_key or os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        endpoint_url = endpoint_url or os.getenv('AWS_ENDPOINT_URL')
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url
        )
        
        # Ensure bucket exists
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.s3_client.create_bucket(Bucket=bucket_name)
                logger.info(f"Created S3 bucket: {bucket_name}")
            else:
                raise
        
        logger.info(f"Using S3 storage with bucket: {bucket_name}")
    
    def _get_object_key(self, project_id: str, file_path: str = None) -> str:
        if file_path:
            return f"projects/{project_id}/{file_path}"
        return f"projects/{project_id}/"
    
    async def save_project(self, session_id: str, files: Dict[str, str], metadata: Dict = None) -> str:
        """Save project to S3"""
        project_id = f"project_{session_id}_{int(datetime.now().timestamp())}"
        
        try:
            # Save files
            for file_path, content in files.items():
                # Remove leading slash
                clean_path = file_path.lstrip('/')
                object_key = self._get_object_key(project_id, clean_path)
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=content.encode('utf-8'),
                    ContentType='text/plain'
                )
            
            # Save metadata
            metadata = metadata or {}
            metadata.update({
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'file_count': len(files)
            })
            
            metadata_key = self._get_object_key(project_id, 'metadata.json')
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Saved project {project_id} to S3 with {len(files)} files")
            return project_id
            
        except Exception as e:
            logger.error(f"Failed to save project {project_id} to S3: {e}")
            raise
    
    async def load_project(self, project_id: str) -> Tuple[Dict[str, str], Dict]:
        """Load project from S3"""
        files = {}
        metadata = {}
        
        try:
            # List all objects in project
            prefix = self._get_object_key(project_id, '')
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            
            if 'Contents' not in response:
                raise FileNotFoundError(f"Project {project_id} not found")
            
            for obj in response['Contents']:
                key = obj['Key']
                relative_path = key[len(prefix):]
                
                # Download file content
                content = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)['Body'].read()
                
                if relative_path == 'metadata.json':
                    metadata = json.loads(content.decode('utf-8'))
                else:
                    files[relative_path] = content.decode('utf-8')
            
            logger.info(f"Loaded project {project_id} from S3 with {len(files)} files")
            return files, metadata
            
        except Exception as e:
            logger.error(f"Failed to load project {project_id} from S3: {e}")
            raise
    
    async def list_projects(self, limit: int = 100) -> List[Dict]:
        """List projects in S3"""
        projects = []
        
        try:
            # List all project prefixes
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='projects/',
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes'][:limit]:
                    project_id = prefix['Prefix'].split('/')[-2]
                    
                    # Try to get metadata
                    try:
                        metadata_key = self._get_object_key(project_id, 'metadata.json')
                        metadata_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                        metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                        
                        projects.append({
                            'project_id': project_id,
                            'session_id': metadata.get('session_id'),
                            'created_at': metadata.get('created_at'),
                            'file_count': metadata.get('file_count', 0),
                            'size': metadata_obj['ContentLength']
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for project {project_id}: {e}")
            
            return sorted(projects, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list projects from S3: {e}")
            return []
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete project from S3"""
        try:
            # List all objects in project
            prefix = self._get_object_key(project_id, '')
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            
            if 'Contents' in response:
                # Delete all objects
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects}
                )
                
                logger.info(f"Deleted project {project_id} from S3")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_id} from S3: {e}")
            return False
    
    async def export_project(self, project_id: str, format: str = "zip") -> bytes:
        """Export project from S3 as zip file"""
        if format.lower() != "zip":
            raise NotImplementedError(f"Export format '{format}' not supported")
        
        import zipfile
        
        try:
            files, metadata = await self.load_project(project_id)
            
            with tempfile.BytesIO() as buffer:
                with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path, content in files.items():
                        zip_file.writestr(file_path, content)
                    
                    # Add metadata
                    zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
                
                return buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to export project {project_id} from S3: {e}")
            raise

def get_storage_manager() -> StorageManager:
    """Get storage manager based on configuration"""
    storage_type = os.getenv('STORAGE_TYPE', 'local').lower()
    
    if storage_type == 's3':
        return S3StorageManager(
            bucket_name=os.getenv('S3_BUCKET_NAME', 'lovable-clone-projects'),
            access_key=os.getenv('AWS_ACCESS_KEY_ID'),
            secret_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            endpoint_url=os.getenv('AWS_ENDPOINT_URL')
        )
    elif storage_type == 'local':
        return LocalStorageManager(
            storage_path=os.getenv('LOCAL_STORAGE_PATH', './projects')
        )
    else:
        raise NotImplementedError(f"Storage type '{storage_type}' not implemented")