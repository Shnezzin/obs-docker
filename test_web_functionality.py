#!/usr/bin/env python3
"""
Comprehensive Test Suite for OBS Docker Web Management Interface
Tests all pages, API endpoints, and functionality
"""

import requests
import json
import time
import sys
import os
from urllib.parse import urljoin

class OBSDockerTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'pages': {},
            'api_endpoints': {},
            'functionality': {},
            'errors': []
        }
    
    def test_page_accessibility(self, page_name, path):
        """Test if a page is accessible and returns valid HTML"""
        try:
            url = urljoin(self.base_url, path)
            response = self.session.get(url, timeout=10)
            
            success = response.status_code == 200
            self.results['pages'][page_name] = {
                'status_code': response.status_code,
                'accessible': success,
                'content_type': response.headers.get('content-type', ''),
                'size': len(response.content)
            }
            
            if success:
                print(f"✅ {page_name} page accessible")
            else:
                print(f"❌ {page_name} page failed (status: {response.status_code})")
                self.results['errors'].append(f"{page_name} page returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ {page_name} page error: {e}")
            self.results['pages'][page_name] = {'error': str(e), 'accessible': False}
            self.results['errors'].append(f"{page_name} page error: {e}")
    
    def test_api_endpoint(self, endpoint_name, path, method='GET', data=None):
        """Test if an API endpoint is accessible and returns valid JSON"""
        try:
            url = urljoin(self.base_url, path)
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=10)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=10)
            else:
                response = self.session.request(method, url, json=data, timeout=10)
            
            success = response.status_code in [200, 201, 202]
            
            try:
                json_data = response.json()
                has_valid_json = True
            except:
                json_data = None
                has_valid_json = False
            
            self.results['api_endpoints'][endpoint_name] = {
                'status_code': response.status_code,
                'accessible': success,
                'has_valid_json': has_valid_json,
                'response_data': json_data
            }
            
            if success:
                print(f"✅ {endpoint_name} API endpoint working")
            else:
                print(f"❌ {endpoint_name} API endpoint failed (status: {response.status_code})")
                self.results['errors'].append(f"{endpoint_name} API returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint_name} API error: {e}")
            self.results['api_endpoints'][endpoint_name] = {'error': str(e), 'accessible': False}
            self.results['errors'].append(f"{endpoint_name} API error: {e}")
    
    def test_docker_connectivity(self):
        """Test if Docker is accessible from the web interface"""
        try:
            response = self.session.get(urljoin(self.base_url, '/api/containers'), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'containers' in data or isinstance(data, dict):
                    print("✅ Docker connectivity working")
                    self.results['functionality']['docker_connectivity'] = True
                else:
                    print("❌ Docker connectivity: Invalid response format")
                    self.results['functionality']['docker_connectivity'] = False
                    self.results['errors'].append("Docker API returned invalid format")
            elif response.status_code == 503:
                print("❌ Docker service not available")
                self.results['functionality']['docker_connectivity'] = False
                self.results['errors'].append("Docker service not available (503)")
            else:
                print(f"❌ Docker connectivity failed (status: {response.status_code})")
                self.results['functionality']['docker_connectivity'] = False
                self.results['errors'].append(f"Docker API returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ Docker connectivity error: {e}")
            self.results['functionality']['docker_connectivity'] = False
            self.results['errors'].append(f"Docker connectivity error: {e}")
    
    def test_instance_creation(self):
        """Test creating a new OBS instance"""
        try:
            test_data = {
                'name': 'test-instance',
                'template': 'streaming',
                'user': 'testuser',
                'password': 'testpass123'
            }
            
            response = self.session.post(
                urljoin(self.base_url, '/api/instances/create'),
                json=test_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('status') == 'success':
                    print("✅ Instance creation working")
                    self.results['functionality']['instance_creation'] = True
                    
                    # Try to clean up the test instance
                    try:
                        self.session.delete(
                            urljoin(self.base_url, '/api/instances/test-instance/remove'),
                            timeout=10
                        )
                    except:
                        pass  # Cleanup failure is not critical
                else:
                    print(f"❌ Instance creation failed: {data.get('message', 'Unknown error')}")
                    self.results['functionality']['instance_creation'] = False
                    self.results['errors'].append(f"Instance creation failed: {data.get('message')}")
            else:
                print(f"❌ Instance creation failed (status: {response.status_code})")
                self.results['functionality']['instance_creation'] = False
                self.results['errors'].append(f"Instance creation returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ Instance creation error: {e}")
            self.results['functionality']['instance_creation'] = False
            self.results['errors'].append(f"Instance creation error: {e}")
    
    def test_static_files(self):
        """Test if static files (CSS, JS) are accessible"""
        static_files = [
            '/static/js/api.js',
            '/static/js/csrf.js'
        ]
        
        accessible_count = 0
        for file_path in static_files:
            try:
                response = self.session.get(urljoin(self.base_url, file_path), timeout=5)
                if response.status_code == 200:
                    accessible_count += 1
                    print(f"✅ Static file accessible: {file_path}")
                else:
                    print(f"❌ Static file not accessible: {file_path} (status: {response.status_code})")
                    self.results['errors'].append(f"Static file {file_path} returned {response.status_code}")
            except Exception as e:
                print(f"❌ Static file error {file_path}: {e}")
                self.results['errors'].append(f"Static file {file_path} error: {e}")
        
        self.results['functionality']['static_files'] = accessible_count == len(static_files)
    
    def run_all_tests(self):
        """Run all tests and generate a comprehensive report"""
        print("🚀 Starting OBS Docker Web Interface Tests")
        print("=" * 60)
        
        # Test page accessibility
        print("\n📄 Testing Page Accessibility:")
        pages = [
            ('Dashboard', '/'),
            ('Instances', '/instances'),
            ('Containers', '/containers'),
            ('Images', '/images'),
            ('Plugins', '/plugins'),
            ('Monitoring', '/monitoring'),
            ('Backups', '/backups'),
            ('Settings', '/settings')
        ]
        
        for page_name, path in pages:
            self.test_page_accessibility(page_name, path)
        
        # Test API endpoints
        print("\n🔌 Testing API Endpoints:")
        api_endpoints = [
            ('System Stats', '/api/system/stats'),
            ('System Info', '/api/system/info'),
            ('Containers', '/api/containers'),
            ('Instances', '/api/instances'),
            ('Images', '/api/images'),
            ('Plugins', '/api/plugins'),
            ('Backups', '/api/backups'),
            ('Performance Profiles', '/api/performance/profiles')
        ]
        
        for endpoint_name, path in api_endpoints:
            self.test_api_endpoint(endpoint_name, path)
        
        # Test functionality
        print("\n⚙️ Testing Core Functionality:")
        self.test_docker_connectivity()
        self.test_static_files()
        
        # Test instance creation (only if Docker is working)
        if self.results['functionality'].get('docker_connectivity', False):
            self.test_instance_creation()
        else:
            print("⏭️ Skipping instance creation test (Docker not available)")
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 TEST REPORT")
        print("=" * 60)
        
        # Page accessibility summary
        total_pages = len(self.results['pages'])
        accessible_pages = sum(1 for page in self.results['pages'].values() if page.get('accessible', False))
        print(f"\n📄 Pages: {accessible_pages}/{total_pages} accessible")
        
        # API endpoints summary
        total_apis = len(self.results['api_endpoints'])
        working_apis = sum(1 for api in self.results['api_endpoints'].values() if api.get('accessible', False))
        print(f"🔌 APIs: {working_apis}/{total_apis} working")
        
        # Functionality summary
        functionality_tests = self.results['functionality']
        working_functions = sum(1 for func in functionality_tests.values() if func)
        total_functions = len(functionality_tests)
        print(f"⚙️ Functions: {working_functions}/{total_functions} working")
        
        # Overall status
        total_tests = total_pages + total_apis + total_functions
        passing_tests = accessible_pages + working_apis + working_functions
        success_rate = (passing_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passing_tests}/{total_tests})")
        
        # Error summary
        if self.results['errors']:
            print(f"\n❌ Errors Found ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"   {i}. {error}")
        else:
            print("\n✅ No errors found!")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if success_rate >= 90:
            print("   🎉 Excellent! The web interface is working well.")
        elif success_rate >= 70:
            print("   👍 Good! Minor issues need attention.")
        elif success_rate >= 50:
            print("   ⚠️ Moderate issues found. Review the errors above.")
        else:
            print("   🚨 Significant issues found. Major fixes needed.")
        
        # VNC/RDP connectivity note
        print("\n🖥️ VNC/RDP Connectivity:")
        print("   To test VNC/RDP connectivity:")
        print("   1. Create an instance via the web interface")
        print("   2. Note the assigned RDP port (usually 3389 or auto-assigned)")
        print("   3. Use an RDP client to connect to localhost:<port>")
        print("   4. Use the username/password specified during instance creation")
        
        # Save detailed report
        report_file = 'obs_docker_test_report.json'
        try:
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n📄 Detailed report saved to: {report_file}")
        except Exception as e:
            print(f"\n❌ Could not save report: {e}")

def main():
    """Main function to run the tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test OBS Docker Web Interface')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL of the web interface (default: http://localhost:8080)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Timeout for requests in seconds (default: 30)')
    
    args = parser.parse_args()
    
    print(f"Testing OBS Docker Web Interface at: {args.url}")
    print("Make sure the web interface is running before starting tests.")
    print("You can start it with: cd web/ && ./start-web-manager.sh start")
    
    # Wait a moment for user to read
    time.sleep(2)
    
    tester = OBSDockerTester(args.url)
    tester.run_all_tests()

if __name__ == '__main__':
    main()