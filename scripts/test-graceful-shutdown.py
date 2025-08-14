#!/usr/bin/env python3
"""
Test script for graceful shutdown functionality.

This script starts the application and tests graceful shutdown behavior.
"""

import asyncio
import signal
import sys
import time
import subprocess
import httpx
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_graceful_shutdown():
    """Test graceful shutdown behavior."""
    print("Testing graceful shutdown functionality...")
    
    # Start the application in a subprocess
    print("Starting application...")
    process = subprocess.Popen([
        sys.executable, "-m", "src.main"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Wait for application to start
    await asyncio.sleep(2)
    
    try:
        # Check if application is running
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/healthz", timeout=5)
                if response.status_code == 200:
                    print("✓ Application started successfully")
                else:
                    print(f"✗ Application health check failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"✗ Failed to connect to application: {e}")
                return False
        
        # Send SIGTERM to trigger graceful shutdown
        print("Sending SIGTERM signal...")
        process.send_signal(signal.SIGTERM)
        
        # Wait for graceful shutdown with timeout
        shutdown_start = time.time()
        timeout = 35  # Slightly longer than default shutdown timeout
        
        while process.poll() is None and (time.time() - shutdown_start) < timeout:
            await asyncio.sleep(0.5)
            print(f"Waiting for shutdown... ({time.time() - shutdown_start:.1f}s)")
        
        if process.poll() is None:
            print("✗ Graceful shutdown timeout, force killing...")
            process.kill()
            process.wait()
            return False
        else:
            shutdown_time = time.time() - shutdown_start
            print(f"✓ Graceful shutdown completed in {shutdown_time:.1f}s")
            
            # Check exit code
            if process.returncode == 0:
                print("✓ Application exited cleanly")
                return True
            else:
                print(f"✗ Application exited with code {process.returncode}")
                return False
    
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
    
    finally:
        # Ensure process is terminated
        if process.poll() is None:
            process.kill()
            process.wait()


async def test_shutdown_with_active_requests():
    """Test graceful shutdown with active requests."""
    print("\nTesting graceful shutdown with active requests...")
    
    # Start the application
    print("Starting application...")
    process = subprocess.Popen([
        sys.executable, "-m", "src.main"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Wait for application to start
    await asyncio.sleep(2)
    
    try:
        # Verify application is running
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/healthz", timeout=5)
                if response.status_code != 200:
                    print(f"✗ Application not ready: {response.status_code}")
                    return False
            except Exception as e:
                print(f"✗ Failed to connect to application: {e}")
                return False
        
        print("✓ Application is ready")
        
        # Start some long-running requests
        async def make_request(client, delay=1):
            try:
                # Make a request that would take some time
                response = await client.get("http://localhost:8000/healthz", timeout=10)
                return response.status_code == 200
            except Exception:
                return False
        
        # Start multiple concurrent requests
        async with httpx.AsyncClient() as client:
            request_tasks = [
                asyncio.create_task(make_request(client, 0.5))
                for _ in range(3)
            ]
            
            # Give requests a moment to start
            await asyncio.sleep(0.1)
            
            # Send shutdown signal
            print("Sending SIGTERM with active requests...")
            process.send_signal(signal.SIGTERM)
            
            # Wait for requests to complete and shutdown
            shutdown_start = time.time()
            
            # Wait for requests to complete
            request_results = await asyncio.gather(*request_tasks, return_exceptions=True)
            print(f"✓ Requests completed: {sum(1 for r in request_results if r is True)} successful")
            
            # Wait for process to exit
            while process.poll() is None and (time.time() - shutdown_start) < 35:
                await asyncio.sleep(0.5)
            
            if process.poll() is None:
                print("✗ Shutdown timeout")
                process.kill()
                return False
            else:
                shutdown_time = time.time() - shutdown_start
                print(f"✓ Graceful shutdown with active requests completed in {shutdown_time:.1f}s")
                return process.returncode == 0
    
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


async def main():
    """Run all graceful shutdown tests."""
    print("=== Graceful Shutdown Test Suite ===\n")
    
    tests = [
        ("Basic graceful shutdown", test_graceful_shutdown),
        ("Graceful shutdown with active requests", test_shutdown_with_active_requests),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"Result: {'PASS' if result else 'FAIL'}\n")
        except Exception as e:
            print(f"ERROR: {e}\n")
            results.append((test_name, False))
    
    # Summary
    print("=== Test Results ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("✓ All graceful shutdown tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test suite failed: {e}")
        sys.exit(1)