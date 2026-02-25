// Travel App JavaScript - Interactive features

// Tab switching
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to clicked button
    event.target.classList.add('active');
    
    // Load specific tab data
    if (tabName === 'itinerary') {
        loadItineraryTimeline();
    }
}

// Load itinerary timeline
async function loadItineraryTimeline() {
    const timelineContainer = document.getElementById('itinerary-timeline');
    const tripId = window.location.pathname.split('/')[2]; // Extract trip ID from URL
    
    if (!tripId) return;
    
    try {
        const response = await fetch(`/api/trip/${tripId}/itineraries-by-date`);
        const data = await response.json();
        
        if (Object.keys(data).length === 0) {
            timelineContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-calendar-alt"></i>
                    <h3>No itineraries yet</h3>
                    <p>Add your first travel plan to see it here!</p>
                </div>
            `;
            return;
        }
        
        let timelineHTML = '<h2><i class="fas fa-clock"></i> Timeline</h2>';
        
        Object.keys(data).sort().forEach(date => {
            const items = data[date];
            const formattedDate = new Date(date).toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
            
            timelineHTML += `<div class="timeline-date">${formattedDate}</div>`;
            
            items.forEach(item => {
                timelineHTML += `
                    <div class="timeline-item">
                        <h4>
                            <i class="fas fa-${getTransportIcon(item.transport)}"></i>
                            ${item.from || 'Unknown'} → ${item.to || 'Unknown'}
                        </h4>
                        <span class="transport-badge">${item.transport || 'Transport'}</span>
                        <div class="timeline-details">
                            ${item.time ? `<span><i class="fas fa-clock"></i> ${item.time}</span>` : ''}
                            ${item.duration ? `<span><i class="fas fa-hourglass-half"></i> ${item.duration}</span>` : ''}
                        </div>
                        ${item.notes ? `<div class="timeline-notes">${item.notes}</div>` : ''}
                    </div>
                `;
            });
        });
        
        timelineContainer.innerHTML = timelineHTML;
        
    } catch (error) {
        console.error('Error loading itinerary:', error);
        timelineContainer.innerHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i>
                Error loading itinerary data
            </div>
        `;
    }
}

// Get transport icon
function getTransportIcon(transport) {
    const icons = {
        'train': 'train',
        'flight': 'plane',
        'bus': 'bus',
        'car': 'car',
        'ferry': 'ship'
    };
    return icons[transport] || 'route';
}

// Auto-estimate travel time when from/to filled
document.addEventListener('DOMContentLoaded', function() {
    const fromInput = document.getElementById('from_location');
    const toInput = document.getElementById('to_location');
    const transportSelect = document.getElementById('transport_mode');
    const durationInput = document.getElementById('duration');
    const tripId = window.location.pathname.split('/')[2];
    
    // Timeline loading is triggered by default tab being active
    // Let it load automatically
    
    // Auto-estimate on blur events
    [fromInput, toInput, transportSelect].forEach(element => {
        if (element) {
            element.addEventListener('blur', async () => {
                if (fromInput.value && toInput.value && !durationInput.value) {
                    try {
                        const response = await fetch(`/api/estimate-travel-time?from=${encodeURIComponent(fromInput.value)}&to=${encodeURIComponent(toInput.value)}&mode=${encodeURIComponent(transportSelect.value)}`);
                        const data = await response.json();
                        if (data.duration) {
                            durationInput.value = data.duration;
                            durationInput.style.color = '#28a745';
                            durationInput.style.fontWeight = 'bold';
                        }
                    } catch (e) {
                        console.log('Could not auto-estimate duration');
                    }
                }
            });
        }
    });
    
    // Loading text
    document.getElementById('timeline-loading').innerHTML = `
        <div style="text-align: center; color: #6c757d;">
            <i class="fas fa-spinner fa-spin"></i> Loading timeline...
        </div>
    `;
});

// QR Code generation for mobile access
function generateQRCode() {
    if (typeof qrcode === 'undefined') return;
    
    const qrcodeDiv = document.getElementById('qrcode');
    if (qrcodeDiv && !qrcodeDiv.innerHTML) {
        const currentUrl = window.location.href;
        new QRCode(qrcodeDiv, {
            text: currentUrl,
            width: 200,
            height: 200,
            colorDark: '#0066cc',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.H
        });
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Delete confirmation
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('[data-action="delete"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
});

// Currency formatter for expense inputs
function formatCurrency(input) {
    const value = parseFloat(input.value);
    if (!isNaN(value)) {
        input.value = value.toFixed(2);
    }
}
