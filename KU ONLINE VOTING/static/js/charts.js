// Kampala University Online Voting System - Dynamic Chart Visualizations

function renderPositionChart(canvasId, labels, data, colors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Votes Received',
                data: data,
                backgroundColor: colors || [
                    '#092347', '#f5a623', '#10b981', '#6366f1',
                    '#ec4899', '#8b5cf6', '#14b8a6', '#f97316'
                ],
                borderRadius: 6,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` ${context.parsed.x} votes`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

function renderDonutChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#092347', '#f5a623', '#10b981', '#3b82f6',
                    '#8b5cf6', '#f43f5e', '#06b6d4', '#eab308'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 14, font: { size: 12 } }
                }
            },
            cutout: '65%'
        }
    });
}
