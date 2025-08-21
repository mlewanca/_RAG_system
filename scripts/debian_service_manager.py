#!/usr/bin/env python3
"""
Debian Service Manager for Enhanced RAG System
Manages systemd services, checks status, and provides maintenance commands
"""

import subprocess
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DebianServiceManager:
    def __init__(self):
        self.services = {
            'ollama': 'Ollama AI model server',
            'rag-api': 'RAG System API server',
            'nginx': 'Nginx web server'
        }
        
        self.required_dirs = [
            '/nvme0n1p2',
            '/nvme0n1p2/config',
            '/nvme0n1p2/logs',
            '/nvme0n1p2/rag-env'
        ]
    
    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """Run a system command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def check_service_status(self, service_name: str) -> Dict[str, any]:
        """Check the status of a systemd service"""
        try:
            # Get service status
            code, stdout, stderr = self.run_command(['systemctl', 'is-active', service_name])
            is_active = stdout.strip() == 'active'
            
            # Get service enabled status
            code, stdout, stderr = self.run_command(['systemctl', 'is-enabled', service_name])
            is_enabled = stdout.strip() == 'enabled'
            
            # Get detailed status
            code, stdout, stderr = self.run_command(['systemctl', 'status', service_name, '--no-pager', '-l'])
            
            return {
                'name': service_name,
                'active': is_active,
                'enabled': is_enabled,
                'status_output': stdout,
                'description': self.services.get(service_name, 'Unknown service')
            }
        except Exception as e:
            return {
                'name': service_name,
                'active': False,
                'enabled': False,
                'error': str(e),
                'description': self.services.get(service_name, 'Unknown service')
            }
    
    def start_service(self, service_name: str) -> bool:
        """Start a systemd service"""
        print(f"🔄 Starting {service_name}...")
        code, stdout, stderr = self.run_command(['sudo', 'systemctl', 'start', service_name])
        
        if code == 0:
            print(f"✅ {service_name} started successfully")
            return True
        else:
            print(f"❌ Failed to start {service_name}: {stderr}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a systemd service"""
        print(f"🔄 Stopping {service_name}...")
        code, stdout, stderr = self.run_command(['sudo', 'systemctl', 'stop', service_name])
        
        if code == 0:
            print(f"✅ {service_name} stopped successfully")
            return True
        else:
            print(f"❌ Failed to stop {service_name}: {stderr}")
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a systemd service"""
        print(f"🔄 Restarting {service_name}...")
        code, stdout, stderr = self.run_command(['sudo', 'systemctl', 'restart', service_name])
        
        if code == 0:
            print(f"✅ {service_name} restarted successfully")
            return True
        else:
            print(f"❌ Failed to restart {service_name}: {stderr}")
            return False
    
    def enable_service(self, service_name: str) -> bool:
        """Enable a systemd service to start on boot"""
        print(f"🔄 Enabling {service_name}...")
        code, stdout, stderr = self.run_command(['sudo', 'systemctl', 'enable', service_name])
        
        if code == 0:
            print(f"✅ {service_name} enabled for auto-start")
            return True
        else:
            print(f"❌ Failed to enable {service_name}: {stderr}")
            return False
    
    def disable_service(self, service_name: str) -> bool:
        """Disable a systemd service from starting on boot"""
        print(f"🔄 Disabling {service_name}...")
        code, stdout, stderr = self.run_command(['sudo', 'systemctl', 'disable', service_name])
        
        if code == 0:
            print(f"✅ {service_name} disabled from auto-start")
            return True
        else:
            print(f"❌ Failed to disable {service_name}: {stderr}")
            return False
    
    def get_service_logs(self, service_name: str, lines: int = 50) -> str:
        """Get recent logs for a service"""
        code, stdout, stderr = self.run_command([
            'sudo', 'journalctl', '-u', service_name, 
            '--no-pager', '-l', f'--lines={lines}'
        ])
        
        if code == 0:
            return stdout
        else:
            return f"Error getting logs: {stderr}"
    
    def follow_service_logs(self, service_name: str):
        """Follow logs for a service in real-time"""
        print(f"📋 Following logs for {service_name} (Ctrl+C to stop)...")
        try:
            subprocess.run([
                'sudo', 'journalctl', '-u', service_name, 
                '--no-pager', '-f'
            ])
        except KeyboardInterrupt:
            print("\n👋 Stopped following logs")
    
    def check_all_services(self) -> Dict[str, Dict]:
        """Check status of all RAG system services"""
        results = {}
        
        print("🔍 Checking all RAG system services...")
        print("=" * 50)
        
        for service_name in self.services.keys():
            status = self.check_service_status(service_name)
            results[service_name] = status
            
            # Print status
            active_icon = "✅" if status['active'] else "❌"
            enabled_icon = "🔄" if status['enabled'] else "⭕"
            
            print(f"{active_icon} {enabled_icon} {service_name:<12} - {status['description']}")
            if not status['active']:
                print(f"   Status: {status.get('status_output', '').split('Active:')[1].split('Docs:')[0].strip() if 'Active:' in status.get('status_output', '') else 'inactive'}")
        
        return results
    
    def check_system_health(self) -> Dict[str, any]:
        """Comprehensive system health check"""
        health = {
            'services': {},
            'directories': {},
            'network': {},
            'resources': {},
            'overall_status': 'unknown'
        }
        
        print("🏥 System Health Check")
        print("=" * 30)
        
        # Check services
        print("\n🔧 Services:")
        health['services'] = self.check_all_services()
        
        # Check directories
        print(f"\n📁 Directories:")
        for dir_path in self.required_dirs:
            exists = Path(dir_path).exists()
            health['directories'][dir_path] = exists
            print(f"{'✅' if exists else '❌'} {dir_path}")
        
        # Check network connectivity
        print(f"\n🌐 Network:")
        network_checks = {
            'ollama_api': self.check_url('http://localhost:11434/api/tags'),
            'nginx': self.check_url('http://localhost:80'),
            'rag_api': self.check_url('http://localhost:8000/health')
        }
        health['network'] = network_checks
        
        for service, status in network_checks.items():
            print(f"{'✅' if status else '❌'} {service}")
        
        # Check system resources
        print(f"\n💾 Resources:")
        health['resources'] = self.check_system_resources()
        
        # Determine overall status
        services_ok = all(s['active'] for s in health['services'].values())
        dirs_ok = all(health['directories'].values())
        network_ok = any(health['network'].values())  # At least one service responding
        
        if services_ok and dirs_ok and network_ok:
            health['overall_status'] = 'healthy'
            print(f"\n🎉 Overall Status: ✅ HEALTHY")
        elif network_ok:
            health['overall_status'] = 'degraded'
            print(f"\n⚠️  Overall Status: 🟡 DEGRADED")
        else:
            health['overall_status'] = 'unhealthy'
            print(f"\n🚨 Overall Status: ❌ UNHEALTHY")
        
        return health
    
    def check_url(self, url: str, timeout: int = 5) -> bool:
        """Check if a URL is accessible"""
        try:
            code, stdout, stderr = self.run_command(['curl', '-s', '--max-time', str(timeout), url])
            return code == 0
        except:
            return False
    
    def check_system_resources(self) -> Dict[str, any]:
        """Check system resource usage"""
        resources = {}
        
        try:
            # Check disk space
            code, stdout, stderr = self.run_command(['df', '-h', '/nvme0n1p2'])
            if code == 0:
                lines = stdout.strip().split('\n')
                if len(lines) > 1:
                    fields = lines[1].split()
                    resources['disk'] = {
                        'used': fields[2] if len(fields) > 2 else 'unknown',
                        'available': fields[3] if len(fields) > 3 else 'unknown',
                        'usage_percent': fields[4] if len(fields) > 4 else 'unknown'
                    }
                    usage_percent = int(fields[4].rstrip('%')) if len(fields) > 4 and fields[4].rstrip('%').isdigit() else 0
                    print(f"{'✅' if usage_percent < 80 else '⚠️' if usage_percent < 90 else '❌'} Disk: {fields[4]} used")
            
            # Check memory
            code, stdout, stderr = self.run_command(['free', '-h'])
            if code == 0:
                lines = stdout.strip().split('\n')
                if len(lines) > 1:
                    fields = lines[1].split()
                    resources['memory'] = {
                        'total': fields[1] if len(fields) > 1 else 'unknown',
                        'used': fields[2] if len(fields) > 2 else 'unknown',
                        'available': fields[6] if len(fields) > 6 else 'unknown'
                    }
                    print(f"✅ Memory: {fields[2]}/{fields[1]} used")
            
            # Check load average
            code, stdout, stderr = self.run_command(['uptime'])
            if code == 0:
                load_avg = stdout.split('load average:')[1].strip() if 'load average:' in stdout else 'unknown'
                resources['load_average'] = load_avg
                print(f"✅ Load average: {load_avg}")
        
        except Exception as e:
            print(f"⚠️  Could not check system resources: {e}")
        
        return resources
    
    def quick_fix(self) -> bool:
        """Attempt to fix common issues automatically"""
        print("🔧 Attempting quick fixes...")
        
        success = True
        
        # Check and start services
        for service_name in self.services.keys():
            status = self.check_service_status(service_name)
            
            if not status['active']:
                print(f"🔄 Service {service_name} is not active, attempting to start...")
                if not self.start_service(service_name):
                    success = False
            
            if not status['enabled']:
                print(f"🔄 Service {service_name} is not enabled, enabling...")
                if not self.enable_service(service_name):
                    success = False
        
        # Wait a moment for services to start
        if not success:
            print("⏳ Waiting for services to start...")
            time.sleep(5)
        
        # Check if fixes worked
        print("\n🔍 Verifying fixes...")
        health = self.check_system_health()
        
        if health['overall_status'] == 'healthy':
            print("✅ Quick fix successful!")
            return True
        else:
            print("⚠️  Some issues remain. Check individual service logs.")
            return False
    
    def maintenance_mode(self, enable: bool = True):
        """Enable or disable maintenance mode"""
        if enable:
            print("🚧 Enabling maintenance mode...")
            # Stop RAG API but keep Ollama running
            self.stop_service('rag-api')
            print("✅ Maintenance mode enabled. RAG API stopped, Ollama still running.")
        else:
            print("🔄 Disabling maintenance mode...")
            # Start RAG API
            self.start_service('rag-api')
            print("✅ Maintenance mode disabled. RAG API restarted.")
    
    def backup_system(self):
        """Create a backup of the system configuration"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"/nvme0n1p2/backups/system_{timestamp}"
        
        print(f"💾 Creating system backup: {backup_dir}")
        
        try:
            # Create backup directory
            Path(backup_dir).mkdir(parents=True, exist_ok=True)
            
            # Backup configuration
            self.run_command(['cp', '-r', '/nvme0n1p2/config', f'{backup_dir}/'])
            
            # Backup systemd services
            service_backup_dir = f"{backup_dir}/systemd"
            Path(service_backup_dir).mkdir(exist_ok=True)
            
            for service in self.services.keys():
                service_file = f"/etc/systemd/system/{service}.service"
                if Path(service_file).exists():
                    self.run_command(['sudo', 'cp', service_file, service_backup_dir])
            
            # Backup nginx config
            nginx_backup_dir = f"{backup_dir}/nginx"
            Path(nginx_backup_dir).mkdir(exist_ok=True)
            self.run_command(['sudo', 'cp', '/etc/nginx/sites-available/rag-system', nginx_backup_dir])
            
            # Create backup manifest
            manifest = {
                'timestamp': timestamp,
                'services': list(self.services.keys()),
                'directories': self.required_dirs,
                'backup_path': backup_dir
            }
            
            with open(f"{backup_dir}/manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            print(f"✅ Backup created successfully: {backup_dir}")
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description="Debian Service Manager for RAG System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check service status")
    status_parser.add_argument("--service", help="Specific service to check")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start service")
    start_parser.add_argument("service", help="Service to start")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop service")
    stop_parser.add_argument("service", help="Service to stop")
    
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart service")
    restart_parser.add_argument("service", help="Service to restart")
    
    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable service")
    enable_parser.add_argument("service", help="Service to enable")
    
    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable service")
    disable_parser.add_argument("service", help="Service to disable")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("service", help="Service to show logs for")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow logs in real-time")
    logs_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines to show")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Comprehensive health check")
    
    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Attempt automatic fixes")
    
    # Maintenance command
    maint_parser = subparsers.add_parser("maintenance", help="Maintenance mode")
    maint_parser.add_argument("action", choices=["enable", "disable"], help="Enable or disable maintenance mode")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create system backup")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = DebianServiceManager()
    
    try:
        if args.command == "status":
            if args.service:
                status = manager.check_service_status(args.service)
                print(json.dumps(status, indent=2))
            else:
                manager.check_all_services()
        
        elif args.command == "start":
            manager.start_service(args.service)
        
        elif args.command == "stop":
            manager.stop_service(args.service)
        
        elif args.command == "restart":
            manager.restart_service(args.service)
        
        elif args.command == "enable":
            manager.enable_service(args.service)
        
        elif args.command == "disable":
            manager.disable_service(args.service)
        
        elif args.command == "logs":
            if args.follow:
                manager.follow_service_logs(args.service)
            else:
                logs = manager.get_service_logs(args.service, args.lines)
                print(logs)
        
        elif args.command == "health":
            manager.check_system_health()
        
        elif args.command == "fix":
            manager.quick_fix()
        
        elif args.command == "maintenance":
            enable = args.action == "enable"
            manager.maintenance_mode(enable)
        
        elif args.command == "backup":
            manager.backup_system()
    
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.error(f"Service manager error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()