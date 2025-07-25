/**
 * API Helper Functions for OBS Docker Manager
 * 
 * This script provides helper functions for making API calls and handling responses.
 */

// Global API configuration
window.API_CONFIG = {
    BASE_URL: window.location.origin,
    TIMEOUT: 30000,
    RETRY_COUNT: 3,
    RETRY_DELAY: 1000
};

/**
 * Make an authenticated API call with proper error handling
 * @param {string} url - The API endpoint URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Object>} - Promise that resolves to the response data
 */
async function apiCall(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        timeout: API_CONFIG.TIMEOUT
    };

    // Merge options
    const finalOptions = { ...defaultOptions, ...options };
    
    // Add CSRF token if available
    const csrfToken = getCSRFToken();
    if (csrfToken && finalOptions.method !== 'GET') {
        finalOptions.headers['X-CSRFToken'] = csrfToken;
        
        // Add CSRF token to body for JSON requests
        if (finalOptions.body && finalOptions.headers['Content-Type'] === 'application/json') {
            try {
                const bodyData = JSON.parse(finalOptions.body);
                bodyData.csrf_token = csrfToken;
                finalOptions.body = JSON.stringify(bodyData);
            } catch (e) {
                console.warn('Could not add CSRF token to request body:', e);
            }
        }
    }

    // Make the request with retry logic
    let lastError;
    for (let attempt = 1; attempt <= API_CONFIG.RETRY_COUNT; attempt++) {
        try {
            const response = await fetchWithTimeout(url, finalOptions);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
                throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Check for API-level errors
            if (data.status === 'error') {
                throw new Error(data.message || 'API returned error status');
            }
            
            return data;
            
        } catch (error) {
            lastError = error;
            console.warn(`API call attempt ${attempt} failed:`, error.message);
            
            // Don't retry on certain errors
            if (error.name === 'AbortError' || 
                error.message.includes('401') || 
                error.message.includes('403') ||
                attempt === API_CONFIG.RETRY_COUNT) {
                break;
            }
            
            // Wait before retrying
            if (attempt < API_CONFIG.RETRY_COUNT) {
                await new Promise(resolve => setTimeout(resolve, API_CONFIG.RETRY_DELAY * attempt));
            }
        }
    }
    
    // All attempts failed
    console.error('API call failed after all retries:', lastError);
    showToast(`API Error: ${lastError.message}`, 'danger');
    throw lastError;
}

/**
 * Fetch with timeout support
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} - Promise that resolves to the response
 */
async function fetchWithTimeout(url, options = {}) {
    const { timeout = 30000, ...fetchOptions } = options;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }
        throw error;
    }
}

/**
 * Make an authenticated request using the legacy method (for compatibility)
 * @param {string} url - The API endpoint URL
 * @param {string} method - HTTP method
 * @param {Object} data - Request data
 * @returns {Promise<Response>} - Promise that resolves to the response
 */
async function makeAuthenticatedRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    // Add CSRF token
    const csrfToken = getCSRFToken();
    if (csrfToken && method !== 'GET') {
        options.headers['X-CSRFToken'] = csrfToken;
    }

    // Add data to request
    if (data && method !== 'GET') {
        if (typeof data === 'object') {
            if (csrfToken) {
                data.csrf_token = csrfToken;
            }
            options.body = JSON.stringify(data);
        } else {
            options.body = data;
        }
    }

    return fetch(url, options);
}

/**
 * Get CSRF token from cookie or meta tag
 * @returns {string} - CSRF token or empty string
 */
function getCSRFToken() {
    // Try to get from meta tag first
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }
    
    // Try to get from cookie
    const name = 'XSRF-TOKEN=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookieArray = decodedCookie.split(';');
    
    for (let i = 0; i < cookieArray.length; i++) {
        let cookie = cookieArray[i].trim();
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length, cookie.length);
        }
    }
    
    return '';
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, danger, warning, info)
 * @param {number} duration - How long to show the toast (ms)
 */
function showToast(message, type = 'info', duration = 5000) {
    // Remove any existing toasts of the same type
    document.querySelectorAll(`.toast.bg-${type}`).forEach(toast => {
        const bsToast = bootstrap.Toast.getInstance(toast);
        if (bsToast) {
            bsToast.hide();
        }
    });

    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${getToastIcon(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { 
        autohide: true, 
        delay: duration 
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function () {
        this.remove();
    });
}

/**
 * Get the appropriate icon for a toast type
 * @param {string} type - Toast type
 * @returns {string} - Font Awesome icon class
 */
function getToastIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-circle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

/**
 * Format bytes to human readable format
 * @param {number} bytes - Number of bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted string
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format a date string to a readable format
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date string
 */
function formatDateTime(dateString) {
    if (!dateString || dateString === 'N/A') return 'Unknown';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;
        
        return date.toLocaleString();
    } catch (e) {
        return dateString;
    }
}

/**
 * Debounce function to limit the rate of function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @param {boolean} immediate - Whether to execute immediately
 * @returns {Function} - Debounced function
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        apiCall,
        makeAuthenticatedRequest,
        getCSRFToken,
        showToast,
        formatBytes,
        formatDateTime,
        debounce
    };
}

// Initialize API helpers when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('API helpers initialized');
    
    // Set up global error handler for unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        showToast('An unexpected error occurred. Please try again.', 'danger');
    });
    
    // Set up global error handler for JavaScript errors
    window.addEventListener('error', function(event) {
        console.error('JavaScript error:', event.error);
        if (event.error && event.error.message && !event.error.message.includes('Script error')) {
            showToast('A JavaScript error occurred. Please refresh the page.', 'warning');
        }
    });
});