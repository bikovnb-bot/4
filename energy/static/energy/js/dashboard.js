// Сохранение настроек дашборда
function saveDashboardSettings() {
    const widgets = Array.from(document.querySelectorAll('.widget-card')).map(card => card.dataset.widgetId);
    const order = widgets;
    const period = document.getElementById('periodSelect').value;
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect')?.value;
    const quarter = document.getElementById('quarterSelect')?.value;
    const resourceType = document.getElementById('resourceTypeSelect').value;
    const threshold = document.getElementById('thresholdInput')?.value;

    fetch('/energy/dashboard/save-settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({
            widgets: widgets,
            order: order,
            period: period,
            year: year,
            month: month,
            quarter: quarter,
            resource_type: resourceType,
            threshold: threshold,
        }),
    }).then(response => response.json()).then(data => {
        if (data.status === 'ok') console.log('Настройки сохранены');
    });
}

// Переключение виджетов (checkbox)
document.querySelectorAll('.widget-toggle').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const widgetId = this.value;
        const card = document.querySelector(`.widget-card[data-widget-id="${widgetId}"]`);
        if (this.checked) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
        saveDashboardSettings();
    });
});

// Drag-and-drop для сортировки (используем SortableJS)
new Sortable(document.getElementById('widgets-container'), {
    animation: 150,
    onEnd: () => saveDashboardSettings(),
});