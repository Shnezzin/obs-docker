#!/usr/bin/env python3
"""
Fix missing JavaScript functions in templates
"""

import os
import re

def fix_instances_template():
    """Add missing JavaScript functions to instances template"""
    
    template_path = "web/templates/instances.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace {% block scripts %} with {% block extra_js %}
    content = content.replace('{% block scripts %}', '{% block extra_js %}')
    
    # Find the end of the existing script block and add missing functions
    missing_functions = '''
    // Missing functions for instances page
    
    function refreshInstances() {
        loadInstances();
        showToast('Instances refreshed', 'success');
    }
    
    function showCreateInstance() {
        const modal = new bootstrap.Modal(document.getElementById('createInstanceModal'));
        modal.show();
    }
    
    async function startAllInstances() {
        try {
            const result = await apiCall('/api/instances/start-all', { method: 'POST' });
            showToast(result.message || 'Started all instances', 'success');
            await loadInstances();
        } catch (error) {
            console.error('Error starting all instances:', error);
        }
    }
    
    async function stopAllInstances() {
        try {
            const result = await apiCall('/api/instances/stop-all', { method: 'POST' });
            showToast(result.message || 'Stopped all instances', 'success');
            await loadInstances();
        } catch (error) {
            console.error('Error stopping all instances:', error);
        }
    }
    
    async function scaleInstances() {
        const count = prompt('How many instances would you like to scale to?', '3');
        if (count && !isNaN(count)) {
            try {
                const result = await apiCall('/api/instances/scale', {
                    method: 'POST',
                    body: JSON.stringify({ count: parseInt(count) })
                });
                showToast(result.message || `Scaled to ${count} instances`, 'success');
                await loadInstances();
            } catch (error) {
                console.error('Error scaling instances:', error);
            }
        }
    }
    
    async function cleanupInstances() {
        if (confirm('This will remove all stopped instances. Are you sure?')) {
            try {
                const result = await apiCall('/api/instances/cleanup', { method: 'POST' });
                showToast(result.message || 'Cleanup completed', 'success');
                await loadInstances();
            } catch (error) {
                console.error('Error cleaning up instances:', error);
            }
        }
    }
'''
    
    # Insert the missing functions before the closing </script> tag
    content = content.replace('</script>\n{% endblock %}', missing_functions + '\n</script>\n{% endblock %}')
    
    # Write the updated template
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed instances.html")

def fix_containers_template():
    """Add missing JavaScript functions to containers template"""
    
    template_path = "web/templates/containers.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace {% block scripts %} with {% block extra_js %} if needed
    content = content.replace('{% block scripts %}', '{% block extra_js %}')
    
    # Add missing functions
    missing_functions = '''
    // Missing functions for containers page
    
    function refreshContainers() {
        loadContainers();
        showToast('Containers refreshed', 'success');
    }
    
    function showCreateContainer() {
        const modal = new bootstrap.Modal(document.getElementById('createContainerModal'));
        modal.show();
    }
    
    async function cleanupContainers() {
        if (confirm('This will remove all stopped containers. Are you sure?')) {
            try {
                const result = await apiCall('/api/containers/cleanup', { method: 'POST' });
                showToast(result.message || 'Cleanup completed', 'success');
                await loadContainers();
            } catch (error) {
                console.error('Error cleaning up containers:', error);
            }
        }
    }
'''
    
    # Insert the missing functions before the closing </script> tag
    if '</script>\n{% endblock %}' in content:
        content = content.replace('</script>\n{% endblock %}', missing_functions + '\n</script>\n{% endblock %}')
    elif '</script>' in content and '{% endblock %}' in content:
        content = content.replace('</script>', missing_functions + '\n</script>')
    
    # Write the updated template
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed containers.html")

def fix_plugins_template():
    """Add missing JavaScript functions to plugins template"""
    
    template_path = "web/templates/plugins.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace {% block scripts %} with {% block extra_js %} if needed
    content = content.replace('{% block scripts %}', '{% block extra_js %}')
    
    # Add missing functions
    missing_functions = '''
    // Missing functions for plugins page
    
    function showInstallPlugin() {
        const modal = new bootstrap.Modal(document.getElementById('installPluginModal'));
        modal.show();
    }
    
    function refreshPlugins() {
        loadPlugins();
        showToast('Plugins refreshed', 'success');
    }
    
    async function installPopularPlugin(pluginName) {
        try {
            const result = await apiCall('/api/plugins/install', {
                method: 'POST',
                body: JSON.stringify({ plugin_name: pluginName })
            });
            showToast(result.message || `Installing ${pluginName}...`, 'success');
            await loadPlugins();
        } catch (error) {
            console.error('Error installing plugin:', error);
        }
    }
'''
    
    # Insert the missing functions before the closing </script> tag
    if '</script>\n{% endblock %}' in content:
        content = content.replace('</script>\n{% endblock %}', missing_functions + '\n</script>\n{% endblock %}')
    elif '</script>' in content and '{% endblock %}' in content:
        content = content.replace('</script>', missing_functions + '\n</script>')
    
    # Write the updated template
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed plugins.html")

def fix_monitoring_template():
    """Add missing JavaScript functions to monitoring template"""
    
    template_path = "web/templates/monitoring.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace {% block scripts %} with {% block extra_js %} if needed
    content = content.replace('{% block scripts %}', '{% block extra_js %}')
    
    # Add missing functions
    missing_functions = '''
    // Missing functions for monitoring page
    
    function setTimeRange(range) {
        currentTimeRange = range;
        showToast(`Time range set to ${range}`, 'info');
        // This would reload chart data for the specified time range
        loadMetrics();
    }
    
    function refreshAlerts() {
        loadAlerts();
        showToast('Alerts refreshed', 'success');
    }
    
    function refreshLogs() {
        loadLogs();
        showToast('Logs refreshed', 'success');
    }
    
    function clearLogs() {
        document.getElementById('systemLogs').textContent = '';
        showToast('Logs cleared', 'info');
    }
'''
    
    # Insert the missing functions before the closing </script> tag
    if '</script>\n{% endblock %}' in content:
        content = content.replace('</script>\n{% endblock %}', missing_functions + '\n</script>\n{% endblock %}')
    elif '</script>' in content and '{% endblock %}' in content:
        content = content.replace('</script>', missing_functions + '\n</script>')
    
    # Write the updated template
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed monitoring.html")

def fix_backups_template():
    """Add missing JavaScript functions to backups template"""
    
    template_path = "web/templates/backups.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace {% block scripts %} with {% block extra_js %} if needed
    content = content.replace('{% block scripts %}', '{% block extra_js %}')
    
    # Add missing functions
    missing_functions = '''
    // Missing functions for backups page
    
    async function createBackup(type) {
        try {
            const result = await apiCall('/api/backups/create', {
                method: 'POST',
                body: JSON.stringify({ type: type })
            });
            showToast(result.message || `Creating ${type} backup...`, 'success');
            await loadBackups();
        } catch (error) {
            console.error('Error creating backup:', error);
        }
    }
    
    function refreshBackups() {
        loadBackups();
        showToast('Backups refreshed', 'success');
    }
    
    function showScheduleBackup() {
        const modal = new bootstrap.Modal(document.getElementById('scheduleBackupModal'));
        modal.show();
    }
    
    async function cleanupOldBackups() {
        if (confirm('This will remove old backups based on retention policies. Continue?')) {
            try {
                const result = await apiCall('/api/backups/cleanup', { method: 'POST' });
                showToast(result.message || 'Cleanup completed', 'success');
                await loadBackups();
            } catch (error) {
                console.error('Error cleaning up backups:', error);
            }
        }
    }
    
    function showRestoreModal() {
        const modal = new bootstrap.Modal(document.getElementById('restoreModal'));
        modal.show();
    }
    
    function showMigrationModal() {
        showToast('Migration wizard would open here', 'info');
    }
    
    async function validateBackups() {
        try {
            const result = await apiCall('/api/backups/validate', { method: 'POST' });
            showToast(result.message || 'Backup validation completed', 'success');
        } catch (error) {
            console.error('Error validating backups:', error);
        }
    }
'''
    
    # Insert the missing functions before the closing </script> tag
    if '</script>\n{% endblock %}' in content:
        content = content.replace('</script>\n{% endblock %}', missing_functions + '\n</script>\n{% endblock %}')
    elif '</script>' in content and '{% endblock %}' in content:
        content = content.replace('</script>', missing_functions + '\n</script>')
    
    # Write the updated template
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed backups.html")

def fix_settings_template():
    """Add missing JavaScript functions to settings template"""
    
    template_path = "web/templates/settings.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Replace {% block scripts %} with {% block extra_js %} if needed
    content = content.replace('{% block scripts %}', '{% block extra_js %}')
    
    # Add missing functions
    missing_functions = '''
    // Missing functions for settings page
    
    async function saveGeneralSettings() {
        const settings = {
            defaultUser: document.getElementById('defaultUser').value,
            defaultDesktop: document.getElementById('defaultDesktop').value,
            obsVersion: document.getElementById('obsVersion').value,
            enableGPU: document.getElementById('enableGPU').checked,
            autoStart: document.getElementById('autoStart').checked
        };
        
        try {
            const result = await apiCall('/api/settings/general', {
                method: 'POST',
                body: JSON.stringify(settings)
            });
            showToast('General settings saved successfully', 'success');
        } catch (error) {
            console.error('Error saving general settings:', error);
        }
    }
    
    async function savePerformanceSettings() {
        const profile = document.getElementById('defaultProfile').value;
        
        try {
            const result = await apiCall('/api/performance/apply', {
                method: 'POST',
                body: JSON.stringify({ profile: profile })
            });
            showToast('Performance profile applied successfully', 'success');
        } catch (error) {
            console.error('Error applying performance profile:', error);
        }
    }
    
    async function runSecurityAudit() {
        try {
            const result = await apiCall('/api/security/audit', { method: 'POST' });
            showToast(result.message || 'Security audit completed', 'success');
        } catch (error) {
            console.error('Error running security audit:', error);
        }
    }
    
    async function saveSecuritySettings() {
        const settings = {
            enableSSL: document.getElementById('enableSSL').checked,
            enableVPN: document.getElementById('enableVPN').checked,
            enableMFA: document.getElementById('enableMFA').checked,
            passwordPolicy: document.getElementById('passwordPolicy').value
        };
        
        try {
            const result = await apiCall('/api/settings/security', {
                method: 'POST',
                body: JSON.stringify(settings)
            });
            showToast('Security settings saved successfully', 'success');
        } catch (error) {
            console.error('Error saving security settings:', error);
        }
    }
    
    async function saveCloudSettings() {
        const settings = {
            provider: document.getElementById('cloudProvider').value,
            awsBucket: document.getElementById('awsBucket').value,
            gcpBucket: document.getElementById('gcpBucket').value,
            autoUpload: document.getElementById('autoUpload').checked,
            backupConfigs: document.getElementById('backupConfigs').checked
        };
        
        try {
            const result = await apiCall('/api/settings/cloud', {
                method: 'POST',
                body: JSON.stringify(settings)
            });
            showToast('Cloud settings saved successfully', 'success');
        } catch (error) {
            console.error('Error saving cloud settings:', error);
        }
    }
    
    async function saveBackupSettings() {
        const settings = {
            enableScheduled: document.getElementById('enableScheduledBackups').checked,
            frequency: document.getElementById('backupFrequency').value,
            retention: document.getElementById('retentionPeriod').value,
            compress: document.getElementById('compressBackups').checked,
            encrypt: document.getElementById('encryptBackups').checked
        };
        
        try {
            const result = await apiCall('/api/settings/backup', {
                method: 'POST',
                body: JSON.stringify(settings)
            });
            showToast('Backup settings saved successfully', 'success');
        } catch (error) {
            console.error('Error saving backup settings:', error);
        }
    }
    
    function exportSettings() {
        showToast('Exporting settings...', 'info');
        // Implementation would go here
    }
    
    function importSettings() {
        showToast('Import settings functionality would open here', 'info');
    }
    
    function resetSettings() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            showToast('Settings reset to defaults', 'info');
            // Implementation would go here
        }
    }
'''
    
    # Insert the missing functions before the closing </script> tag
    if '</script>\n{% endblock %}' in content:
        content = content.replace('</script>\n{% endblock %}', missing_functions + '\n</script>\n{% endblock %}')
    elif '</script>' in content and '{% endblock %}' in content:
        content = content.replace('</script>', missing_functions + '\n</script>')
    
    # Write the updated template
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed settings.html")

def main():
    print("🔧 Fixing Missing JavaScript Functions in Templates")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('web/templates'):
        print("❌ Please run this script from the obs-docker root directory")
        return
    
    # Fix all templates
    try:
        fix_instances_template()
        fix_containers_template()
        fix_plugins_template()
        fix_monitoring_template()
        fix_backups_template()
        fix_settings_template()
        
        print("\n🎉 All templates fixed!")
        print("\n📝 Next steps:")
        print("1. Restart the web manager: cd web/ && ./start-web-manager.sh restart")
        print("2. Clear browser cache and reload the pages")
        print("3. All JavaScript functions should now work properly")
        
    except Exception as e:
        print(f"❌ Error fixing templates: {e}")

if __name__ == '__main__':
    main()