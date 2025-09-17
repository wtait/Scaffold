import os
import tempfile
import shutil
import subprocess
import logging
import asyncio
from typing import Dict, Optional, Tuple
from pathlib import Path
from abc import ABC, abstractmethod
import json
import tarfile
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SandboxManager(ABC):
    """Abstract base class for sandbox implementations"""
    
    @abstractmethod
    async def create_sandbox(self, session_id: str) -> Dict[str, str]:
        """Create a new sandbox and return connection info"""
        pass
    
    @abstractmethod
    async def connect_sandbox(self, sandbox_id: str) -> Dict[str, str]:
        """Connect to existing sandbox"""
        pass
    
    @abstractmethod
    async def upload_files(self, sandbox_id: str, file_map: Dict[str, str]) -> bool:
        """Upload files to sandbox"""
        pass
    
    @abstractmethod
    async def download_files(self, sandbox_id: str, paths: list) -> Dict[str, bytes]:
        """Download files from sandbox"""
        pass
    
    @abstractmethod
    async def execute_command(self, sandbox_id: str, command: str, args: list = None) -> Tuple[str, str, int]:
        """Execute command in sandbox. Returns (stdout, stderr, exit_code)"""
        pass
    
    @abstractmethod
    async def get_url(self, sandbox_id: str) -> str:
        """Get the public URL for the sandbox"""
        pass
    
    @abstractmethod
    async def cleanup_sandbox(self, sandbox_id: str) -> bool:
        """Clean up sandbox resources"""
        pass

class DockerSandboxManager(SandboxManager):
    """Docker-based sandbox implementation for local development"""
    
    def __init__(self, base_image: str = None, working_dir: str = "/app"):
        self.base_image = base_image or "lovable-clone-sandbox:latest"
        self.working_dir = working_dir
        self.containers: Dict[str, str] = {}  # session_id -> container_id
        self.ports: Dict[str, int] = {}  # session_id -> port
        self._next_port = 3100  # Start from 3100 to avoid conflict with frontend
        
    async def _get_next_port(self) -> int:
        """Get next available port"""
        while True:
            port = self._next_port
            self._next_port += 1
            if await self._is_port_available(port):
                return port
    
    async def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for use"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "netstat", "-tuln",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            # Check if port is already in use
            port_line = f":{port} "
            return port_line.encode() not in stdout
        except Exception:
            # If netstat fails, try a different approach
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                return True
            except OSError:
                return False
    
    async def _cleanup_existing_container(self, container_name: str):
        """Remove existing container if it exists"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # First try to stop the container
                stop_proc = await asyncio.create_subprocess_exec(
                    "docker", "stop", container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await stop_proc.communicate()
                
                # Then remove it
                proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    logger.info(f"Successfully removed existing container: {container_name}")
                    # Wait a bit for Docker daemon to fully clean up
                    await asyncio.sleep(1)
                    return
                else:
                    logger.warning(f"Failed to remove container {container_name} (attempt {attempt + 1}): {stderr.decode()}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # Wait before retry
            except Exception as e:
                logger.warning(f"Failed to cleanup container {container_name} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
    
    async def _setup_container_template(self, container_id: str):
        """Setup a minimal React template in container"""
        
        # Create a minimal React app instead of cloning a heavy template
        minimal_setup = """
mkdir -p /app/src/components/ui /app/src/lib
cd /app

# Create minimal package.json
cat > package.json << 'EOF'
{
  "name": "react-app",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.87.4",
    "react-router-dom": "^7.9.1",
    "recharts": "^3.2.0",
    "sonner": "^2.0.7",
    "uuid": "^13.0.0",
    "zod": "^4.1.8",
    "react-hook-form": "^7.62.0",
    "@hookform/resolvers": "^5.2.2",
    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.4.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.24"
  }
}
EOF

# Create minimal vite.config.ts
cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000
  }
})
EOF

# Create minimal index.html
cat > index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>React App</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
EOF

# Create minimal App.tsx
cat > src/App.tsx << 'EOF'
import React from 'react'

function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Welcome to Your App</h1>
      <p>This is a minimal React application ready for customization.</p>
    </div>
  )
}

export default App
EOF

# Create minimal main.tsx
cat > src/main.tsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
EOF

# Create minimal index.css
cat > src/index.css << 'EOF'
body {
  margin: 0;
  padding: 0;
  font-family: Arial, sans-serif;
  background-color: #f5f5f5;
}

* {
  box-sizing: border-box;
}
EOF

# Create tsconfig.json
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF

echo "Minimal React template created successfully"

# Create Tailwind config
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

# Create PostCSS config
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

echo "Tailwind configuration files created"
"""
        
        try:
            logger.info(f"Setting up minimal React template in container {container_id}")
            result = await self._run_in_container(container_id, minimal_setup)
            stdout, stderr, exit_code = result
            
            if exit_code != 0:
                logger.error(f"Template setup failed with exit code {exit_code}")
                logger.error(f"stderr: {stderr}")
                raise Exception(f"Failed to setup minimal template: {stderr}")
            else:
                logger.info(f"Minimal template setup completed successfully")
                
        except Exception as e:
            logger.error(f"Template setup failed: {e}")
            raise
    
    async def _start_dev_server(self, container_id: str):
        """Start the dev server in background (dependencies already installed)"""
        startup_script = """
# Start dev server in background
nohup npm run dev > /dev/null 2>&1 &

# Wait a moment for server to start
sleep 3

echo "Dev server started successfully"
"""
        
        try:
            logger.info(f"Starting dev server for container {container_id}")
            result = await self._run_in_container(container_id, startup_script)
            stdout, stderr, exit_code = result
            
            if exit_code != 0:
                logger.warning(f"Dev server startup had issues (exit code {exit_code})")
                logger.warning(f"stderr: {stderr}")
                # Don't raise exception - container is still usable
            else:
                logger.info(f"Dev server started successfully for container {container_id}")
                
        except Exception as e:
            logger.warning(f"Failed to start dev server automatically: {e}")
            # Don't raise exception - user can still use the container
    
    async def _run_in_container(self, container_id: str, command: str) -> Tuple[str, str, int]:
        """Run command in container"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "exec", container_id, "sh", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode(), stderr.decode(), proc.returncode
        except Exception as e:
            logger.error(f"Error running command in container: {e}")
            return "", str(e), -1
    
    async def create_sandbox(self, session_id: str) -> Dict[str, str]:
        """Create a new Docker container sandbox"""
        # Add timestamp to ensure unique container names
        import time
        timestamp = int(time.time())
        container_name = f"sandbox-{session_id}-{timestamp}"
        
        try:
            # Clean up any existing container with the same name
            await self._cleanup_existing_container(container_name)
            
            port = await self._get_next_port()
            
            # Create container with port mapping
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "-d",
                "-p", f"{port}:3000",
                "--name", container_name,
                "-w", self.working_dir,
                self.base_image,
                "tail", "-f", "/dev/null",  # Keep container running
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise Exception(f"Failed to create container: {stderr.decode()}")
            
            container_id = stdout.decode().strip()
            self.containers[session_id] = container_id
            self.ports[session_id] = port
            
            # Start dev server automatically (dependencies already installed in image)
            await self._start_dev_server(container_id)
            
            logger.info(f"Sandbox ready for container {container_id}")
            
            url = f"http://localhost:{port}"
            
            return {
                "sandbox_id": container_id,
                "session_id": session_id,
                "url": url,
                "port": str(port),
                "status": "ready"
            }
            
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            # Cleanup on failure
            await self._cleanup_existing_container(container_name)
            raise
    
    async def connect_sandbox(self, sandbox_id: str) -> Dict[str, str]:
        """Connect to existing sandbox"""
        try:
            # Check if container exists and is running
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", sandbox_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise Exception(f"Container {sandbox_id} not found")
            
            # Find the session_id and port from our records
            session_id = None
            port = None
            
            for sid, cid in self.containers.items():
                if cid == sandbox_id:
                    session_id = sid
                    port = self.ports.get(sid)
                    break
            
            if not session_id or not port:
                raise Exception(f"Sandbox {sandbox_id} not in active sessions")
            
            return {
                "sandbox_id": sandbox_id,
                "session_id": session_id,
                "url": f"http://localhost:{port}",
                "port": str(port),
                "status": "connected"
            }
            
        except Exception as e:
            logger.error(f"Failed to connect to sandbox: {e}")
            raise
    
    async def upload_files(self, sandbox_id: str, file_map: Dict[str, str]) -> bool:
        """Upload files to Docker container"""
        try:
            for file_path, content in file_map.items():
                # Create temporary file
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                try:
                    # Ensure parent directory exists in container
                    parent_dir = str(Path(file_path).parent)
                    await self._run_in_container(sandbox_id, f"mkdir -p {parent_dir}")
                    
                    # Copy file to container
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "cp", tmp_path, f"{sandbox_id}:{file_path}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await proc.communicate()
                    
                    if proc.returncode != 0:
                        logger.error(f"Failed to upload {file_path}: {stderr.decode()}")
                        return False
                        
                finally:
                    # Clean up temp file
                    os.unlink(tmp_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload files: {e}")
            return False
    
    async def download_files(self, sandbox_id: str, paths: list) -> Dict[str, bytes]:
        """Download files from Docker container"""
        files = {}
        
        try:
            for path in paths:
                with tempfile.NamedTemporaryFile() as tmp:
                    # Copy file from container
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "cp", f"{sandbox_id}:{path}", tmp.name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await proc.communicate()
                    
                    if proc.returncode == 0:
                        with open(tmp.name, 'rb') as f:
                            files[path] = f.read()
                    else:
                        logger.warning(f"Failed to download {path}: {stderr.decode()}")
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to download files: {e}")
            return {}
    
    async def execute_command(self, sandbox_id: str, command: str, args: list = None) -> Tuple[str, str, int]:
        """Execute command in Docker container"""
        if args:
            full_command = f"{command} {' '.join(args)}"
        else:
            full_command = command
            
        return await self._run_in_container(sandbox_id, full_command)
    
    async def get_url(self, sandbox_id: str) -> str:
        """Get the public URL for the sandbox"""
        session_id = None
        for sid, cid in self.containers.items():
            if cid == sandbox_id:
                session_id = sid
                break
        
        if session_id and session_id in self.ports:
            port = self.ports[session_id]
            return f"http://localhost:{port}"
        
        raise Exception(f"Sandbox {sandbox_id} not found")
    
    async def cleanup_sandbox(self, sandbox_id: str) -> bool:
        """Clean up Docker container"""
        try:
            # Stop and remove container
            proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", sandbox_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            # Clean up from our records
            session_to_remove = None
            for sid, cid in self.containers.items():
                if cid == sandbox_id:
                    session_to_remove = sid
                    break
            
            if session_to_remove:
                del self.containers[session_to_remove]
                if session_to_remove in self.ports:
                    del self.ports[session_to_remove]
            
            return proc.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox: {e}")
            return False

# Factory function to get the appropriate sandbox manager
def get_sandbox_manager() -> SandboxManager:
    """Get sandbox manager based on environment configuration"""
    sandbox_type = os.getenv("SANDBOX_TYPE", "docker").lower()
    
    if sandbox_type == "docker":
        return DockerSandboxManager()
    else:
        raise NotImplementedError(f"Sandbox type '{sandbox_type}' not implemented")