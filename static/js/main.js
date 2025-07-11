document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar on mobile
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            document.querySelector('.content-wrapper').classList.toggle('expanded');
        });
    }
    
    // Handle flash message dismiss
    document.querySelectorAll('.alert .close').forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });
    
    // Auto-dismiss flash messages after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            alert.style.display = 'none';
        });
    }, 5000);
    
    // Initialize tooltips
    if (window.bootstrap && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Handle attendance actions
    document.querySelectorAll('.attendance-action').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.getAttribute('data-action');
            const url = this.getAttribute('data-url');
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: `action=${action}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.message || 'An error occurred');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred');
            });
        });
    });
    
    // Handle form submissions with fetch
    document.querySelectorAll('form.ajax-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitButton = this.querySelector('[type="submit"]');
            const originalText = submitButton.textContent;
            
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            
            fetch(this.action, {
                method: this.method,
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else if (data.success) {
                    if (data.message) {
                        showAlert('success', data.message);
                    }
                    if (this.dataset.resetOnSuccess === 'true') {
                        this.reset();
                    }
                } else {
                    showAlert('danger', data.message || 'An error occurred');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('danger', 'An error occurred');
            })
            .finally(() => {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            });
        });
    });
    
    function showAlert(type, message) {
        const alertsContainer = document.querySelector('.alerts-container') || document.body;
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        alertsContainer.prepend(alert);
        
        setTimeout(() => {
            alert.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => {
                alert.remove();
            }, 150);
        }, 5000);
    }
});
