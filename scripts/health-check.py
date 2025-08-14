#!/usr/bin/env python3
"""
Health check script for Docker containers.

This script performs health checks for the application and its dependencies,
supporting graceful shutdown scenarios.
"""

import asyncio
import sys
import time
import httpx
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Health checker for application and dependencies.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 5):
        """
        Initialize health checker.
        
        Args:
            base_url: Base URL for health checks
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health check results
        """
        results = {
            "timestamp": time.time(),
            "status": "healthy",
            "checks": {}
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check application health
                app_health = await self._check_app_health(client)
                results["checks"]["application"] = app_health
                
                # Check readiness (dependencies)
                readiness = await self._check_readiness(client)
                results["checks"]["readiness"] = readiness
                
                # Determine overall status
                if not app_health.get("healthy", False):
                    results["status"] = "unhealthy"
                elif not readiness.get("ready", False):
                    results["status"] = "not_ready"
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            results["status"] = "unhealthy"
            results["error"] = str(e)
        
        return results
    
    async def _check_app_health(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """
        Check application health endpoint.
        
        Args:
            client: HTTP client
            
        Returns:
            Application health status
        """
        try:
            response = await client.get(f"{self.base_url}/healthz")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "healthy": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "data": data
                }
            else:
                return {
                    "healthy": False,
                    "status_code": response.status_code,
                    "error": f"Unexpected status code: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_readiness(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """
        Check application readiness endpoint.
        
        Args:
            client: HTTP client
            
        Returns:
            Application readiness status
        """
        try:
            response = await client.get(f"{self.base_url}/readyz")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "ready": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "data": data
                }
            else:
                return {
                    "ready": False,
                    "status_code": response.status_code,
                    "error": f"Unexpected status code: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "ready": False,
                "error": str(e)
            }
    
    async def wait_for_shutdown(self, max_wait: int = 30) -> bool:
        """
        Wait for application to shut down gracefully.
        
        Args:
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if shutdown completed, False if timeout
        """
        logger.info(f"Waiting for graceful shutdown (max {max_wait}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    response = await client.get(f"{self.base_url}/healthz")
                    
                    # If we get a response, app is still running
                    if response.status_code == 200:
                        await asyncio.sleep(1)
                        continue
                    else:
                        # Non-200 response might indicate shutdown in progress
                        logger.info("Application returning non-200 status, shutdown may be in progress")
                        await asyncio.sleep(1)
                        continue
                        
            except (httpx.ConnectError, httpx.TimeoutException):
                # Connection refused or timeout - app likely shut down
                logger.info("Application appears to have shut down")
                return True
            except Exception as e:
                logger.warning(f"Unexpected error during shutdown wait: {e}")
                await asyncio.sleep(1)
        
        logger.warning(f"Shutdown wait timeout ({max_wait}s) exceeded")
        return False


async def main():
    """Main health check function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Health check for API application")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for health checks")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    parser.add_argument("--wait-shutdown", type=int, help="Wait for graceful shutdown (seconds)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    checker = HealthChecker(base_url=args.url, timeout=args.timeout)
    
    if args.wait_shutdown:
        # Wait for graceful shutdown
        success = await checker.wait_for_shutdown(args.wait_shutdown)
        sys.exit(0 if success else 1)
    else:
        # Perform health check
        results = await checker.check_health()
        
        if args.verbose:
            import json
            print(json.dumps(results, indent=2))
        
        # Exit with appropriate code
        if results["status"] == "healthy":
            logger.info("Health check passed")
            sys.exit(0)
        elif results["status"] == "not_ready":
            logger.warning("Application not ready")
            sys.exit(1)
        else:
            logger.error("Health check failed")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())