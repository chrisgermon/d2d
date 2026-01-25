(() => {
    async function loadDeploymentInfo() {
        const target = document.getElementById('deployment-info');
        if (!target) {
            return;
        }

        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            const deploymentTimestamp = (data.deployment_timestamp || '').trim();
            target.textContent = deploymentTimestamp || 'Unknown';
        } catch (error) {
            target.textContent = 'Unknown';
        }
    }

    window.addEventListener('load', loadDeploymentInfo);
})();
