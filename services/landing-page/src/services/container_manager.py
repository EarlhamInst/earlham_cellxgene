"""
Container Manager Service

Manages dynamic CellXGene container instances for dataset viewing.
Allows multiple users to view different datasets simultaneously.

Constitutional Alignment:
- Principle III (Resource Management): Efficient container lifecycle management
- Principle IV (Fail-Fast): Validates before launching
"""

import docker
import logging
import time
from datetime import datetime
from typing import Dict, Tuple, Optional
from pathlib import Path


class CellxgeneContainerManager:
    """Manages dynamic CellXGene container instances."""
    
    def __init__(self, data_directory: str, network_name: str = "cellxgene_stack_cellxgene-network", host_data_directory: str = None):
        """
        Initialize container manager.
        
        Args:
            data_directory: Path to datasets directory (inside container)
            network_name: Docker network name for containers
            host_data_directory: Path to datasets on Docker host (for volume mounting)
        """
        self.logger = logging.getLogger(__name__)
        self.client = docker.from_env()
        self.data_directory = Path(data_directory)
        self.host_data_directory = Path(host_data_directory) if host_data_directory else self.data_directory
        self.network_name = network_name
        self.active_containers: Dict[str, Tuple[object, int, datetime]] = {}  # {dataset_id: (container, port, last_accessed)}
        self.port_range = (5006, 5100)
        
        self.logger.info(f"Container manager initialized for network: {network_name}")
        self.logger.info(f"Host data directory: {self.host_data_directory}")
    
    def _find_free_port(self) -> int:
        """Find an available port in the configured range."""
        used_ports = {port for _, port, _ in self.active_containers.values()}
        
        for port in range(self.port_range[0], self.port_range[1]):
            if port not in used_ports:
                # Verify port is not used by other containers
                try:
                    containers = self.client.containers.list(
                        filters={"publish": f"{port}"}
                    )
                    if not containers:
                        return port
                except Exception as e:
                    self.logger.warning(f"Error checking port {port}: {e}")
                    continue
        
        raise RuntimeError(f"No free ports available in range {self.port_range}")
    
    def launch_dataset(self, dataset_id: str, dataset_filename: str) -> int:
        """
        Launch a CellXGene container for a specific dataset.
        
        Args:
            dataset_id: Unique dataset identifier
            dataset_filename: H5AD filename in the data directory
            
        Returns:
            Port number where the container is accessible
            
        Raises:
            FileNotFoundError: If dataset file doesn't exist
            RuntimeError: If container launch fails
        """
        self.logger.info(f"Launch request for dataset: {dataset_id}, filename: {dataset_filename}")
        
        # Check if already running
        if dataset_id in self.active_containers:
            container, port, _ = self.active_containers[dataset_id]
            try:
                # Verify container is still running
                container.reload()
                if container.status == 'running':
                    self.logger.info(f"Container for {dataset_id} already running on port {port}")
                    # Update last accessed time
                    self.active_containers[dataset_id] = (container, port, datetime.now())
                    return port
                else:
                    # Container stopped, remove from tracking
                    self.logger.warning(f"Container for {dataset_id} not running, restarting")
                    del self.active_containers[dataset_id]
            except docker.errors.NotFound:
                # Container no longer exists
                del self.active_containers[dataset_id]
        
        self.logger.info(f"Checking for existing container: cellxgene-{dataset_id}")
        
        # Check if container exists but not in our tracking (e.g., from previous session)
        try:
            existing_container = self.client.containers.get(f"cellxgene-{dataset_id}")
            self.logger.info(f"Found existing container with status: {existing_container.status}")
            if existing_container.status == 'running':
                # Get the port from existing container
                ports = existing_container.attrs.get('NetworkSettings', {}).get('Ports', {})
                port_bindings = ports.get('5005/tcp', [])
                if port_bindings and len(port_bindings) > 0:
                    port = int(port_bindings[0]['HostPort'])
                    self.active_containers[dataset_id] = (existing_container, port, datetime.now())
                    self.logger.info(f"Reusing existing container for {dataset_id} on port {port}")
                    return port
                else:
                    self.logger.warning(f"Existing container for {dataset_id} has no port bindings, removing")
                    existing_container.remove(force=True)
            else:
                # Container exists but not running, remove it
                self.logger.info(f"Removing stopped container for {dataset_id}")
                existing_container.remove(force=True)
        except docker.errors.NotFound:
            # No existing container, proceed to create new one
            self.logger.info(f"No existing container found for {dataset_id}")
        except Exception as e:
            self.logger.error(f"Error checking for existing container: {e}", exc_info=True)
        
        # Validate dataset file exists
        dataset_path = self.data_directory / dataset_filename
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
        
        # Find available port
        port = self._find_free_port()
        
        self.logger.info(f"Launching CellXGene for {dataset_id} ({dataset_filename}) on port {port}")
        
        try:
            # Launch container with memory limit to prevent OOM issues
            # Default 4GB should handle most datasets; very large datasets may need more
            container = self.client.containers.run(
                "cellxgene_stack-cellxgene",
                detach=True,
                name=f"cellxgene-{dataset_id}",
                environment={
                    "DATASET_FILE": dataset_filename,
                    "DATA_DIRECTORY": "/data/datasets"
                },
                ports={'5005/tcp': port},
                volumes={
                    str(self.host_data_directory.resolve()): {
                        'bind': '/data/datasets',
                        'mode': 'ro'
                    }
                },
                network=self.network_name,
                mem_limit='4g',  # Limit memory to prevent OOM crashes
                memswap_limit='4g',  # Disable swap for consistent performance
                remove=True,  # Auto-remove when stopped
                auto_remove=True
            )
            
            # Wait for container to be healthy
            # Large files (e.g., 4.5GB) can take 2-3 minutes to load
            self._wait_for_healthy(container, timeout=180)
            
            self.active_containers[dataset_id] = (container, port, datetime.now())
            self.logger.info(f"Successfully launched container for {dataset_id} on port {port}")
            
            return port
            
        except Exception as e:
            self.logger.error(f"Failed to launch container for {dataset_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to launch CellXGene container: {str(e)}")
    
    def _wait_for_healthy(self, container, timeout: int = 60):
        """Wait for container to be healthy and responding."""
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        
        # First wait for container to be running
        while time.time() - start_time < timeout:
            try:
                container.reload()
                if container.status == 'running':
                    break
            except docker.errors.NotFound:
                raise RuntimeError("Container disappeared during startup")
            time.sleep(0.5)
        else:
            raise RuntimeError(f"Container did not start within {timeout} seconds")
        
        # Now wait for the application to be responding
        # CellXGene typically takes 5-15 seconds to initialize
        container_name = container.name
        health_check_url = f"http://{container_name}:5005/"
        
        self.logger.info(f"Container {container_name} running, waiting for application to be ready...")
        
        while time.time() - start_time < timeout:
            try:
                # Try to connect to the container's health endpoint
                req = urllib.request.Request(health_check_url, method='GET')
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status in [200, 301, 302]:
                        self.logger.info(f"Container {container_name} is healthy and responding")
                        return
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                # Application not ready yet, keep waiting
                self.logger.debug(f"Waiting for {container_name} to be ready: {e}")
                time.sleep(1)
            except Exception as e:
                self.logger.warning(f"Health check error for {container_name}: {e}")
                time.sleep(1)
        
        raise RuntimeError(f"Container did not become healthy within {timeout} seconds")
    
    def stop_dataset(self, dataset_id: str):
        """Stop a CellXGene container for a dataset."""
        if dataset_id not in self.active_containers:
            self.logger.warning(f"No active container found for {dataset_id}")
            return
        
        container, port, _ = self.active_containers[dataset_id]
        
        try:
            self.logger.info(f"Stopping container for {dataset_id} on port {port}")
            container.stop(timeout=10)
            del self.active_containers[dataset_id]
            self.logger.info(f"Successfully stopped container for {dataset_id}")
        except Exception as e:
            self.logger.error(f"Error stopping container for {dataset_id}: {e}")
            # Still remove from tracking
            del self.active_containers[dataset_id]
    
    def cleanup_inactive(self, max_inactive_seconds: int = 3600):
        """
        Clean up containers that have been inactive for too long.
        
        Args:
            max_inactive_seconds: Maximum inactive time before cleanup (default 60 minutes)
        """
        to_remove = []
        current_time = datetime.now()
        
        for dataset_id, (container, port, last_accessed) in self.active_containers.items():
            try:
                # Check if container is still running
                container.reload()
                if container.status != 'running':
                    self.logger.info(f"Container {dataset_id} is not running, marking for removal")
                    to_remove.append(dataset_id)
                    continue
                
                # Check inactivity time
                inactive_seconds = (current_time - last_accessed).total_seconds()
                if inactive_seconds > max_inactive_seconds:
                    self.logger.info(
                        f"Container {dataset_id} inactive for {inactive_seconds:.0f}s "
                        f"(max: {max_inactive_seconds}s), marking for removal"
                    )
                    to_remove.append(dataset_id)
                    
            except docker.errors.NotFound:
                self.logger.warning(f"Container {dataset_id} not found, marking for removal")
                to_remove.append(dataset_id)
            except Exception as e:
                self.logger.error(f"Error checking container {dataset_id}: {e}", exc_info=True)
                to_remove.append(dataset_id)
        
        # Stop inactive containers
        for dataset_id in to_remove:
            self.stop_dataset(dataset_id)
        
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} inactive container(s)")
    
    def get_container_port(self, dataset_id: str) -> Optional[int]:
        """Get the port for an active container."""
        if dataset_id in self.active_containers:
            return self.active_containers[dataset_id][1]
        return None
    
    def is_container_ready(self, dataset_id: str) -> bool:
        """Check if a container is running and ready."""
        if dataset_id not in self.active_containers:
            return False
        
        container, port, _ = self.active_containers[dataset_id]
        try:
            container.reload()
            return container.status == 'running'
        except docker.errors.NotFound:
            return False
        except Exception:
            return False
    
    def update_access_time(self, dataset_id: str):
        """Update the last access time for a container."""
        if dataset_id in self.active_containers:
            container, port, _ = self.active_containers[dataset_id]
            self.active_containers[dataset_id] = (container, port, datetime.now())
            self.logger.debug(f"Updated access time for container {dataset_id}")
    
    def list_active_containers(self) -> Dict[str, int]:
        """List all active containers and their ports."""
        return {
            dataset_id: port
            for dataset_id, (_, port, _) in self.active_containers.items()
        }
