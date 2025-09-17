import tempfile
import logging
import json
from pathlib import Path
from typing import Dict, Tuple

from .sandbox_manager import get_sandbox_manager

logger = logging.getLogger(__name__)

DEFAULT_CODE_PATH = "/app/src"
DEFAULT_PROJECT_ROOT = "/app"

class SandboxTools:
    """Tools for managing sandbox environments and code operations"""
    
    def __init__(self):
        self.sandbox_manager = get_sandbox_manager()
    
    async def create_app_environment(self, session_id: str) -> dict:
        """Create a new sandbox environment for the session"""
        logger.info(f"Creating app environment for session {session_id}...")
        
        try:
            sandbox_data = await self.sandbox_manager.create_sandbox(session_id)
            logger.info(f"React app created and started successfully! Access it at: {sandbox_data.get('url')}")
            return sandbox_data
        except Exception as e:
            logger.error(f"Failed to create app environment for session {session_id}: {e}")
            raise
    
    async def connect_existing_sandbox(self, session_id: str, sandbox_id: str, sandbox_url: str) -> dict:
        """Connect to an existing sandbox"""
        logger.info(f"Connecting to existing sandbox {sandbox_id} for session {session_id}...")
        
        try:
            sandbox_data = await self.sandbox_manager.connect_sandbox(sandbox_id)
            logger.info(f"Connected to existing sandbox: {sandbox_data.get('url')}")
            return sandbox_data
        except Exception as e:
            logger.error(f"Failed to connect to existing sandbox {sandbox_id}: {e}")
            raise
    
    async def load_code(self, sandbox_id: str) -> Tuple[Dict[str, str], str]:
        """Load code files from sandbox"""
        logger.info(f"Loading code for sandbox {sandbox_id}")
        
        try:
            # Get all files in the source directory
            src_files = []
            self._collect_files(DEFAULT_CODE_PATH, src_files)
            
            # Download files from sandbox
            file_contents = await self.sandbox_manager.download_files(sandbox_id, src_files)
            
            # Convert bytes to string for text files
            file_map = {}
            for file_path, content_bytes in file_contents.items():
                try:
                    file_map[file_path] = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    logger.warning(f"Skipping binary file: {file_path}")
            
            # Get package.json
            package_files = await self.sandbox_manager.download_files(
                sandbox_id, [f"{DEFAULT_PROJECT_ROOT}/package.json"]
            )
            
            package_json = "{}"
            package_path = f"{DEFAULT_PROJECT_ROOT}/package.json"
            if package_path in package_files:
                package_json = package_files[package_path].decode('utf-8')
            else:
                # If no package.json, return a default one
                default_package = {
                    "name": "react-app",
                    "version": "0.1.0",
                    "type": "module",
                    "scripts": {
                        "dev": "vite",
                        "build": "vite build",
                        "preview": "vite preview"
                    },
                    "dependencies": {
                        "@hookform/resolvers": "^5.2.2",
                        "@tanstack/react-query": "^5.87.4",
                        "date-fns": "^4.1.0",
                        "react": "^18.2.0",
                        "react-dom": "^18.2.0",
                        "react-hook-form": "^7.62.0",
                        "react-router-dom": "^7.9.1",
                        "recharts": "^3.2.0",
                        "sonner": "^2.0.7",
                        "uuid": "^13.0.0",
                        "zod": "^4.1.8"
                    }
                }
                package_json = json.dumps(default_package, indent=2)
            
            logger.info(f"Loaded {len(file_map)} files from sandbox {sandbox_id}")
            return file_map, package_json
            
        except Exception as e:
            logger.error(f"Failed to load code from sandbox {sandbox_id}: {e}")
            raise
    
    def _collect_files(self, directory: str, file_list: list, extensions: list = None):
        """Collect file paths recursively (helper for load_code)"""
        if extensions is None:
            extensions = ['.js', '.jsx', '.ts', '.tsx', '.css', '.json', '.html', '.md']
        
        # This is a simplified version - in a real implementation,
        # you'd need to query the sandbox for the actual file structure
        common_files = [
            f"{directory}/App.tsx",
            f"{directory}/App.css",
            f"{directory}/main.tsx",
            f"{directory}/index.css",
            f"{directory}/vite-env.d.ts",
            f"{directory}/components/ui/button.tsx",
            f"{directory}/components/ui/input.tsx",
            f"{directory}/components/ui/textarea.tsx",
            f"{directory}/lib/utils.ts",
        ]
        file_list.extend(common_files)
    
    async def edit_code(self, sandbox_id: str, code_map: Dict[str, str]) -> dict:
        """Edit code files in sandbox"""
        logger.info(f"Editing {len(code_map)} files in sandbox {sandbox_id}")
        
        try:
            # Upload files to sandbox
            success = await self.sandbox_manager.upload_files(sandbox_id, code_map)
            
            if not success:
                raise Exception("Failed to upload files to sandbox")
            
            logger.info(f"Successfully edited {len(code_map)} files in sandbox {sandbox_id}")
            return {"sandbox_id": sandbox_id}
            
        except Exception as e:
            logger.error(f"Failed to edit code in sandbox {sandbox_id}: {e}")
            raise

# Legacy function wrappers for backward compatibility
async def create_app_environment(session_id: str) -> dict:
    """Legacy wrapper for create_app_environment"""
    tools = SandboxTools()
    return await tools.create_app_environment(session_id)

async def load_code(sandbox_id: str) -> Tuple[Dict[str, str], str]:
    """Legacy wrapper for load_code"""
    tools = SandboxTools()
    return await tools.load_code(sandbox_id)

async def edit_code(sandbox_id: str, code_map: Dict[str, str]) -> dict:
    """Legacy wrapper for edit_code"""
    tools = SandboxTools()
    return await tools.edit_code(sandbox_id, code_map)