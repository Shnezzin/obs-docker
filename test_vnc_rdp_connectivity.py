#!/usr/bin/env python3
"""
VNC/RDP Connectivity Test for OBS Docker Containers
Tests the ability to connect to containers via VNC and RDP
"""

import socket
import subprocess
import time
import sys
import os
import requests
import json
from urllib.parse import urljoin

class VNCRDPTester:
    def __init__(self, web_url="http://localhost:8080"):
        self.web_url = web_url
        self.session = requests.Session()
        self.test_results = {
            'container_creation': False,
            'rdp_port_accessible': False,
            'vnc_port_accessible': False,
            'container_health': False,
            'desktop_environment': False,
            'errors': []
        }
    
    def log(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_port_connectivity(self, host, port, timeout=5):
        """Test if a port is accessible"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            self.log(f"Port test error for {host}:{port} - {e}", "ERROR")
            return False
    
    def create_test_container(self):
        """Create a test container for VNC/RDP testing"""
        self.log("Creating test container for VNC/RDP testing...")
        
        test_data = {
            'name': 'vnc-rdp-test',
            'template': 'streaming',
            'user': 'testuser',
            'password': 'TestPass123!'
        }
        
        try:
            response = self.session.post(
                urljoin(self.web_url, '/api/instances/create'),
                json=test_data,
                timeout=60  # Container creation can take time
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('status') == 'success':
                    self.log("✅ Test container created successfully")
                    self.test_results['container_creation'] = True
                    return data.get('instance', {})
                else:
                    error_msg = data.get('message', 'Unknown error')
                    self.log(f"❌ Container creation failed: {error_msg}", "ERROR")
                    self.test_results['errors'].append(f"Container creation failed: {error_msg}")
                    return None
            else:
                self.log(f"❌ Container creation failed (HTTP {response.status_code})", "ERROR")
                self.test_results['errors'].append(f"Container creation HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ Container creation error: {e}", "ERROR")
            self.test_results['errors'].append(f"Container creation error: {e}")
            return None
    
    def wait_for_container_ready(self, container_name, max_wait=120):
        """Wait for container to be ready and running"""
        self.log(f"Waiting for container '{container_name}' to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(
                    urljoin(self.web_url, '/api/instances'),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    instances = data.get('instances', {})
                    
                    # Look for our container
                    container_info = None
                    for name, info in instances.items():
                        if container_name in name or info.get('instance_name') == container_name:
                            container_info = info
                            break
                    
                    if container_info:
                        status = container_info.get('status', '')
                        if status == 'running':
                            self.log("✅ Container is running")
                            return container_info
                        else:
                            self.log(f"Container status: {status}")
                    else:
                        self.log("Container not found in instances list")
                
            except Exception as e:
                self.log(f"Error checking container status: {e}", "ERROR")
            
            time.sleep(5)
        
        self.log("❌ Container did not become ready within timeout", "ERROR")
        self.test_results['errors'].append("Container startup timeout")
        return None
    
    def test_container_health(self, container_name):
        """Test container health and services"""
        self.log("Testing container health...")
        
        try:
            # Try to debug RDP connection
            response = self.session.post(
                urljoin(self.web_url, f'/api/container/{container_name}/debug-rdp'),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.log("✅ Container health check passed")
                    self.test_results['container_health'] = True
                    
                    # Check debug logs for service status
                    debug_logs = data.get('debug', [])
                    for log_entry in debug_logs:
                        if 'XRDP service is running' in log_entry:
                            self.log("✅ XRDP service is running")
                        elif 'D-Bus service is running' in log_entry:
                            self.log("✅ D-Bus service is running")
                        elif 'Desktop environment' in log_entry:
                            self.log("✅ Desktop environment detected")
                            self.test_results['desktop_environment'] = True
                    
                    return True
                else:
                    error_msg = data.get('message', 'Health check failed')
                    self.log(f"❌ Container health check failed: {error_msg}", "ERROR")
                    self.test_results['errors'].append(f"Health check failed: {error_msg}")
            else:
                self.log(f"❌ Health check request failed (HTTP {response.status_code})", "ERROR")
                self.test_results['errors'].append(f"Health check HTTP error: {response.status_code}")
                
        except Exception as e:
            self.log(f"❌ Container health check error: {e}", "ERROR")
            self.test_results['errors'].append(f"Health check error: {e}")
        
        return False
    
    def test_rdp_connectivity(self, container_info):
        """Test RDP port connectivity"""
        self.log("Testing RDP connectivity...")
        
        rdp_port = None
        ports = container_info.get('ports', {})
        
        # Extract RDP port
        if isinstance(ports, dict):
            rdp_port = ports.get('rdp')
            if not rdp_port and 'rdp_port' in container_info:
                rdp_port = container_info['rdp_port']
        
        if rdp_port:
            try:
                rdp_port = int(rdp_port)
                self.log(f"Testing RDP connectivity on port {rdp_port}")
                
                if self.test_port_connectivity('localhost', rdp_port):
                    self.log("✅ RDP port is accessible")
                    self.test_results['rdp_port_accessible'] = True
                    
                    # Try to get more detailed connection info
                    self.log(f"RDP connection details:")
                    self.log(f"  Host: localhost")
                    self.log(f"  Port: {rdp_port}")
                    self.log(f"  Username: {container_info.get('user', 'testuser')}")
                    self.log(f"  Password: [configured during creation]")
                    
                    return True
                else:
                    self.log(f"❌ RDP port {rdp_port} is not accessible", "ERROR")
                    self.test_results['errors'].append(f"RDP port {rdp_port} not accessible")
            except ValueError:
                self.log(f"❌ Invalid RDP port: {rdp_port}", "ERROR")
                self.test_results['errors'].append(f"Invalid RDP port: {rdp_port}")
        else:
            self.log("❌ No RDP port found in container info", "ERROR")
            self.test_results['errors'].append("No RDP port found")
        
        return False
    
    def test_vnc_connectivity(self, container_info):
        """Test VNC port connectivity"""
        self.log("Testing VNC connectivity...")
        
        vnc_port = None
        ports = container_info.get('ports', {})
        
        # Extract VNC port
        if isinstance(ports, dict):
            vnc_port = ports.get('vnc')
        
        # Try common VNC ports if not specified
        if not vnc_port:
            common_vnc_ports = [5900, 5901, 5902]
            for port in common_vnc_ports:
                if self.test_port_connectivity('localhost', port):
                    vnc_port = port
                    break
        
        if vnc_port:
            try:
                vnc_port = int(vnc_port)
                self.log(f"Testing VNC connectivity on port {vnc_port}")
                
                if self.test_port_connectivity('localhost', vnc_port):
                    self.log("✅ VNC port is accessible")
                    self.test_results['vnc_port_accessible'] = True
                    
                    self.log(f"VNC connection details:")
                    self.log(f"  Host: localhost")
                    self.log(f"  Port: {vnc_port}")
                    self.log(f"  Password: [same as RDP password]")
                    
                    return True
                else:
                    self.log(f"❌ VNC port {vnc_port} is not accessible", "ERROR")
                    self.test_results['errors'].append(f"VNC port {vnc_port} not accessible")
            except ValueError:
                self.log(f"❌ Invalid VNC port: {vnc_port}", "ERROR")
                self.test_results['errors'].append(f"Invalid VNC port: {vnc_port}")
        else:
            self.log("⚠️ No VNC port found - this may be normal", "WARN")
        
        return False
    
    def cleanup_test_container(self, container_name):
        """Clean up the test container"""
        self.log("Cleaning up test container...")
        
        try:
            response = self.session.delete(
                urljoin(self.web_url, f'/api/instances/{container_name}/remove'),
                timeout=30
            )
            
            if response.status_code == 200:
                self.log("✅ Test container cleaned up successfully")
            else:
                self.log(f"⚠️ Container cleanup failed (HTTP {response.status_code})", "WARN")
                
        except Exception as e:
            self.log(f"⚠️ Container cleanup error: {e}", "WARN")
    
    def run_connectivity_tests(self):
        """Run all VNC/RDP connectivity tests"""
        self.log("🚀 Starting VNC/RDP Connectivity Tests")
        self.log("=" * 60)
        
        # Step 1: Create test container
        container_info = self.create_test_container()
        if not container_info:
            self.log("❌ Cannot proceed without a test container", "ERROR")
            return self.generate_report()
        
        container_name = container_info.get('name', 'vnc-rdp-test')
        
        try:
            # Step 2: Wait for container to be ready
            container_info = self.wait_for_container_ready(container_name)
            if not container_info:
                return self.generate_report()
            
            # Step 3: Test container health
            self.test_container_health(container_name)
            
            # Step 4: Test RDP connectivity
            self.test_rdp_connectivity(container_info)
            
            # Step 5: Test VNC connectivity
            self.test_vnc_connectivity(container_info)
            
        finally:
            # Step 6: Cleanup
            self.cleanup_test_container(container_name)
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        self.log("=" * 60)
        self.log("📊 VNC/RDP CONNECTIVITY TEST REPORT")
        self.log("=" * 60)
        
        # Test results summary
        tests = [
            ('Container Creation', self.test_results['container_creation']),
            ('Container Health', self.test_results['container_health']),
            ('Desktop Environment', self.test_results['desktop_environment']),
            ('RDP Port Accessible', self.test_results['rdp_port_accessible']),
            ('VNC Port Accessible', self.test_results['vnc_port_accessible'])
        ]
        
        passed_tests = 0
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name}: {status}")
            if result:
                passed_tests += 1
        
        # Overall assessment
        success_rate = (passed_tests / len(tests)) * 100
        self.log(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{len(tests)})")
        
        # Connectivity assessment
        if self.test_results['rdp_port_accessible']:
            self.log("\n✅ RDP CONNECTIVITY: WORKING")
            self.log("   You can connect to containers using any RDP client")
            self.log("   Use the container's assigned port and credentials")
        else:
            self.log("\n❌ RDP CONNECTIVITY: NOT WORKING")
            self.log("   Check container logs and service status")
        
        if self.test_results['vnc_port_accessible']:
            self.log("\n✅ VNC CONNECTIVITY: WORKING")
            self.log("   You can connect to containers using any VNC client")
        else:
            self.log("\n⚠️ VNC CONNECTIVITY: NOT DETECTED")
            self.log("   VNC may not be configured or enabled")
        
        # Error summary
        if self.test_results['errors']:
            self.log(f"\n❌ ERRORS FOUND ({len(self.test_results['errors'])}):")
            for i, error in enumerate(self.test_results['errors'], 1):
                self.log(f"   {i}. {error}")
        
        # Recommendations
        self.log("\n💡 RECOMMENDATIONS:")
        
        if success_rate >= 80:
            self.log("   🎉 Excellent! VNC/RDP connectivity is working well")
            self.log("   You can create containers and connect to them remotely")
        elif success_rate >= 60:
            self.log("   👍 Good! Minor connectivity issues may exist")
            self.log("   Check the errors above for specific issues")
        else:
            self.log("   🚨 Significant connectivity issues found")
            self.log("   Review container configuration and service status")
        
        # Usage instructions
        self.log("\n🖥️ HOW TO CONNECT TO CONTAINERS:")
        self.log("   1. Create a container via the web interface")
        self.log("   2. Wait for it to start (status: running)")
        self.log("   3. Note the assigned RDP port in the web interface")
        self.log("   4. Use an RDP client:")
        self.log("      - Windows: Built-in Remote Desktop Connection")
        self.log("      - macOS: Microsoft Remote Desktop (App Store)")
        self.log("      - Linux: rdesktop, xfreerdp, or Remmina")
        self.log("   5. Connect to: localhost:<port>")
        self.log("   6. Use the username/password from container creation")
        
        # Save report
        try:
            report_file = 'vnc_rdp_test_report.json'
            with open(report_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            self.log(f"\n📄 Detailed report saved to: {report_file}")
        except Exception as e:
            self.log(f"⚠️ Could not save report: {e}", "WARN")
        
        return self.test_results

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test VNC/RDP connectivity for OBS Docker')
    parser.add_argument('--url', default='http://localhost:8080',
                       help='Web interface URL (default: http://localhost:8080)')
    
    args = parser.parse_args()
    
    print("🖥️ VNC/RDP Connectivity Tester for OBS Docker")
    print("This will create a test container and verify remote connectivity")
    print(f"Web interface: {args.url}")
    print("\nMake sure the OBS Docker web interface is running!")
    print("Start it with: cd web/ && ./start-web-manager.sh start")
    
    # Wait for user confirmation
    try:
        input("\nPress Enter to continue or Ctrl+C to cancel...")
    except KeyboardInterrupt:
        print("\nTest cancelled by user")
        return
    
    tester = VNCRDPTester(args.url)
    results = tester.run_connectivity_tests()
    
    # Exit with appropriate code
    if results['rdp_port_accessible'] or results['vnc_port_accessible']:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == '__main__':
    main()