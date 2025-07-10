let chart;
let currentMetric = 'power_w';
let isZoomed = false;
let updateInterval;
let costUpdateTimeout;
let gpuDataset = null;

function updateCurrentTime() {
    const now = new Date();
    const options = { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    };
    document.getElementById('currentTime').textContent = now.toLocaleDateString('en-US', options);
}

function createChart(data, metric) {
    const ctx = document.getElementById('powerChart').getContext('2d');
    
    if (chart) {
        chart.destroy();
    }

    // Filter out null values and create corresponding timestamps
    const validData = [];
    const validLabels = [];
    data[metric].forEach((value, index) => {
        if (value !== null) {
            validData.push(value);
            validLabels.push(data.timestamp[index]);
        }
    });

    // Prepare GPU data if available
    let gpuData = [];
    if (data.gpu_usage) {
        data.gpu_usage.forEach((value, index) => {
            if (value !== null) {
                gpuData.push(value);
            }
        });
    }

    const datasets = [{
        data: validData,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.1)',
        borderWidth: 2,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 5,
        hitRadius: 20,
        fill: true
    }];

    // Add GPU dataset if checkbox is checked
    if (document.getElementById('showGpu').checked && gpuData.length > 0) {
        datasets.push({
            data: gpuData,
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 5,
            hitRadius: 20,
            fill: true
        });
    }

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: validLabels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            animation: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'x'
                    },
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x',
                        onZoom: function() {
                            isZoomed = true;
                            updateZoomStatus();
                            if (updateInterval) {
                                clearInterval(updateInterval);
                                updateInterval = null;
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10
                    }
                },
                y: {
                    beginAtZero: false,
                    suggestedMin: function(context) {
                        const values = context.chart.data.datasets[0].data;
                        const min = Math.min(...values);
                        return Math.max(0, min - (min * 0.1));
                    },
                    suggestedMax: function(context) {
                        const values = context.chart.data.datasets[0].data;
                        const max = Math.max(...values);
                        return max + (max * 0.1);
                    }
                }
            }
        }
    });
}

function getMetricLabel(metric) {
    switch(metric) {
        case 'current_ma': return 'Current (mA)';
        case 'power_w': return 'Power (W)';
        case 'voltage_v': return 'Voltage (V)';
        default: return metric;
    }
}

function switchMetric(metric) {
    currentMetric = metric;
    updateChart();
    
    // Update button highlighting
    document.querySelectorAll('.controls button').forEach(btn => {
        btn.classList.remove('active');
        console.log(`comparing ${btn.id.toLowerCase()} with ${metric}`)
        if (btn.id.toLowerCase().includes(metric)) {
            btn.classList.add('active');
        }
    });
}

function updateChart() {
    const avgInterval = document.getElementById('avgInterval') ? document.getElementById('avgInterval').value : '5s';
    fetch(`/data?avg=${encodeURIComponent(avgInterval)}`)
        .then(response => response.json())
        .then(data => {
            createChart(data, currentMetric);
        });
}

function resetZoom() {
    if (chart) {
        chart.resetZoom();
        isZoomed = false;
        updateZoomStatus();
        startAutoUpdate();
    }
}

function updateZoomStatus() {
    const statusElement = document.getElementById('zoomStatus');
    if (isZoomed) {
        statusElement.textContent = 'Graph zoomed - updates paused';
    } else {
        statusElement.textContent = '';
    }
}

// Debounce function to prevent too many updates while typing
function debouncedUpdateCost(value) {
    clearTimeout(costUpdateTimeout);
    costUpdateTimeout = setTimeout(() => {
        const cost = parseFloat(document.getElementById('costInput').value);
        const usage = parseFloat(document.getElementById('usageInput').value);
        if (!isNaN(cost) && cost >= 0 && !isNaN(usage) && usage >= 0 && usage <= 24) {
            updateCost(cost, usage);
        }
    }, 100);
}

function updateCost(cost, usage) {
    fetch('/update_cost', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            cost: cost,
            usage_hours: usage
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateCostDisplay();
        } else {
            console.error('Error updating cost:', data.error);
        }
    });
}

function updateCostDisplay() {
    fetch('/costs')
        .then(response => response.json())
        .then(costs => {
            document.getElementById('dayCost').textContent = `${costs.day.toFixed(2)}€`;
            document.getElementById('weekCost').textContent = `${costs.week.toFixed(2)}€`;
            document.getElementById('monthCost').textContent = `${costs.month.toFixed(2)}€`;
            document.getElementById('yearCost').textContent = `${costs.year.toFixed(2)}€`;
        });
}

function startAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    updateInterval = setInterval(() => {
        if (!isZoomed) {
            updateChart();
            updateCurrentTime();
            updateCostDisplay();
            // Check recording status
            fetch('/recording_status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('recordStats').checked = data.is_recording;
                });
        }
    }, 5000);
}

function toggleGpu() {
    updateChart();
}

function toggleRecording() {
    const checkbox = document.getElementById('recordStats');
    const isRecording = checkbox.checked;
    
    fetch('/toggle_recording', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ record: isRecording })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Error toggling recording:', data.error);
            checkbox.checked = !isRecording; // Revert the checkbox if there was an error
        }
    })
    .catch(error => {
        console.error('Error:', error);
        checkbox.checked = !isRecording; // Revert the checkbox if there was an error
    });
}

function updateStatistics() {
    fetch('/statistics')
        .then(response => response.json())
        .then(stats => {
            document.getElementById('totalKwh').textContent = `${stats.total_kwh} kWh`;
            document.getElementById('totalTime').textContent = `Recorded over ${stats.total_hours} hours`;
            document.getElementById('avgKwhPerDay').textContent = `${stats.avg_kwh_per_day} kWh/day`;
            document.getElementById('peakPower').textContent = `${stats.peak_power} W`;
            document.getElementById('medianPower').textContent = `${stats.median_power} W`;
            document.getElementById('minPower').textContent = `${stats.min_power} W`;
        })
        .catch(error => console.error('Error fetching statistics:', error));
}

// Update statistics every 30 seconds
setInterval(updateStatistics, 30000);

// Initial statistics update
updateStatistics();

// Initial load
updateChart();
updateCurrentTime();
updateCostDisplay();
// Check initial recording status
fetch('/recording_status')
    .then(response => response.json())
    .then(data => {
        document.getElementById('recordStats').checked = data.is_recording;
    });
startAutoUpdate(); 

// Initialize cost and usage input fields from config
fetch('/config')
    .then(response => response.json())
    .then(config => {
        if (typeof config.electricity_cost_per_kwh === 'number') {
            document.getElementById('costInput').value = config.electricity_cost_per_kwh;
        }
        if (typeof config.usage_hours === 'number') {
            document.getElementById('usageInput').value = config.usage_hours;
        }
    }); 