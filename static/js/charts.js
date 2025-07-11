// Global chart instances to prevent memory leaks
let attendanceChart = null;
let performanceChart = null;
let activityChart = null;

// Initialize all charts on the page
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    
    // Update charts initially and set interval
    updateCharts();
    setInterval(updateCharts, 300000); // Update every 5 minutes
});

// Clean up charts when page is unloaded
window.addEventListener('beforeunload', function() {
    destroyAllCharts();
});

function destroyAllCharts() {
    if (attendanceChart) {
        attendanceChart.destroy();
        attendanceChart = null;
    }
    if (performanceChart) {
        performanceChart.destroy();
        performanceChart = null;
    }
    if (activityChart) {
        activityChart.destroy();
        activityChart = null;
    }
}

function initializeCharts() {
    // Destroy existing charts first
    destroyAllCharts();
    
    // Attendance doughnut chart
    const attendanceChartEl = document.getElementById('attendanceChart');
    if (attendanceChartEl) {
        const ctx = attendanceChartEl.getContext('2d');
        attendanceChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Present', 'Late', 'Absent'],
                datasets: [{
                    data: [70, 15, 15], // Default data, will be updated via API
                    backgroundColor: [
                        '#28a745',
                        '#ffc107',
                        '#dc3545'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.raw}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Performance bar chart
    const performanceChartEl = document.getElementById('performanceChart');
    if (performanceChartEl) {
        const ctx = performanceChartEl.getContext('2d');
        performanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Task Completion', 'Report Quality', 'Attendance', 'Initiative'],
                datasets: [{
                    label: 'Performance Metrics',
                    data: [85, 90, 95, 80],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(153, 102, 255, 0.7)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Score (%)'
                        }
                    }
                }
            }
        });
    }

    // Activity timeline
    const activityChartEl = document.getElementById('activityChart');
    if (activityChartEl) {
        const ctx = activityChartEl.getContext('2d');
        activityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
                datasets: [{
                    label: 'Tasks Completed',
                    data: [3, 5, 6, 8, 10, 12],
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.3,
                    fill: true
                }, {
                    label: 'Reports Submitted',
                    data: [1, 2, 2, 3, 3, 4],
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });
    }
}

// Update charts with real data
function updateCharts() {
    // Only update if chart exists
    if (attendanceChart) {
        // Attendance chart
        fetch('/api/attendance/stats')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (attendanceChart && !attendanceChart.destroyed) {
                    attendanceChart.data.datasets[0].data = [
                        data.present_days || 0,
                        data.late_days || 0,
                        data.absent_days || 0
                    ];
                    attendanceChart.update();
                }
            })
            .catch(error => {
                console.error('Error updating attendance chart:', error);
            });
    }
}
