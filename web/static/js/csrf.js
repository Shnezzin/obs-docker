/**
 * CSRF Token Handling for OBS Docker Manager
 * 
 * This script handles CSRF token management for AJAX requests and forms.
 * It automatically adds the CSRF token to all AJAX requests and forms.
 */

// Get CSRF token from cookie
function getCSRFToken() {
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

// Add CSRF token to all AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        // Skip for GET/HEAD/OPTIONS requests or cross-domain requests
        if (!/^(GET|HEAD|OPTIONS)$/i.test(settings.type) && !this.crossDomain) {
            const token = getCSRFToken();
            if (token) {
                xhr.setRequestHeader('X-CSRFToken', token);
                
                // Also add to form data if it's a form submission
                if (settings.data && settings.contentType === 'application/x-www-form-urlencoded') {
                    if (typeof settings.data === 'string') {
                        settings.data += '&csrf_token=' + encodeURIComponent(token);
                    } else if (typeof settings.data === 'object') {
                        settings.data.csrf_token = token;
                    }
                }
            }
        }
    }
});

// Add CSRF token to all forms
$(document).ready(function() {
    // Add CSRF token to all forms
    $('form').each(function() {
        // Skip if already has a CSRF token
        if ($(this).find('input[name="csrf_token"]').length === 0) {
            const token = getCSRFToken();
            if (token) {
                $('<input>').attr({
                    type: 'hidden',
                    name: 'csrf_token',
                    value: token
                }).appendTo($(this));
            }
        }
    });

    // Make sure all AJAX requests include the CSRF token
    $(document).ajaxError(function(event, jqXHR, settings, error) {
        if (jqXHR.status === 403 && jqXHR.responseJSON && jqXHR.responseJSON.code === 'CSRF_VALIDATION_FAILED') {
            // CSRF token expired or invalid, reload the page to get a new one
            showAlert('danger', 'Session expired. Please refresh the page and try again.');
            // Redirect to login after a delay
            setTimeout(function() {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
            }, 2000);
        }
    });
});

// Helper function to make authenticated API calls
function makeAuthenticatedRequest(url, method = 'GET', data = null) {
    const token = getCSRFToken();
    const headers = {
        'X-CSRFToken': token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };

    // For non-GET requests, include the CSRF token in the request body
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
        if (data) {
            if (typeof data === 'object') {
                data.csrf_token = token;
            } else if (typeof data === 'string') {
                try {
                    const parsed = JSON.parse(data);
                    parsed.csrf_token = token;
                    data = JSON.stringify(parsed);
                } catch (e) {
                    // If we can't parse as JSON, append as form data
                    data = data + '&csrf_token=' + encodeURIComponent(token);
                }
            }
        } else {
            data = { csrf_token: token };
        }
    }

    return $.ajax({
        url: url,
        method: method,
        headers: headers,
        data: data,
        dataType: 'json'
    });
}

// Override the default fetch to include CSRF token
const originalFetch = window.fetch;
window.fetch = function(resource, init = {}) {
    // Don't modify cross-origin requests
    if (typeof resource === 'string' && !resource.startsWith('/') && !resource.startsWith(window.location.origin)) {
        return originalFetch(resource, init);
    }

    const token = getCSRFToken();
    if (!token) {
        return originalFetch(resource, init);
    }

    // Add CSRF token to headers
    const headers = new Headers(init.headers || {});
    if (!headers.has('X-CSRFToken')) {
        headers.append('X-CSRFToken', token);
    }

    // For non-GET requests, add CSRF token to the body if it's a form submission
    const method = (init.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
        if (init.body) {
            // Handle FormData
            if (init.body instanceof FormData) {
                if (!init.body.has('csrf_token')) {
                    init.body.append('csrf_token', token);
                }
            }
            // Handle URLSearchParams
            else if (init.body instanceof URLSearchParams) {
                if (!init.body.has('csrf_token')) {
                    init.body.append('csrf_token', token);
                }
            }
            // Handle plain objects or JSON strings
            else if (typeof init.body === 'object' || (typeof init.body === 'string' && init.body.trim().startsWith('{'))) {
                let bodyObj = {};
                
                try {
                    // Parse if it's a JSON string
                    if (typeof init.body === 'string') {
                        bodyObj = JSON.parse(init.body);
                    } else {
                        bodyObj = { ...init.body };
                    }
                    
                    // Add CSRF token if not present
                    if (!bodyObj.csrf_token) {
                        bodyObj.csrf_token = token;
                        init.body = JSON.stringify(bodyObj);
                        
                        // Ensure content-type is set to JSON
                        if (!headers.has('Content-Type')) {
                            headers.set('Content-Type', 'application/json');
                        }
                    }
                } catch (e) {
                    console.error('Error processing request body:', e);
                }
            }
        } else {
            // If no body, add CSRF token as form data
            init.body = new URLSearchParams({ csrf_token: token });
            if (!headers.has('Content-Type')) {
                headers.set('Content-Type', 'application/x-www-form-urlencoded');
            }
        }
    }

    // Update headers in the init object
    init.headers = headers;

    // Call the original fetch with updated init
    return originalFetch(resource, init);
};

// Helper function to show alerts
function showAlert(type, message, container = '.alert-container', dismissible = true) {
    const alertDiv = $(`<div class="alert alert-${type} ${dismissible ? 'alert-dismissible fade show' : ''}" role="alert">
        ${message}
        ${dismissible ? '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' : ''}
    </div>`);
    
    // Add to container or body if container not found
    const $container = $(container);
    if ($container.length) {
        $container.prepend(alertDiv);
    } else {
        $('body').prepend(alertDiv);
    }
    
    // Auto-dismiss after 5 seconds
    if (dismissible) {
        setTimeout(() => {
            alertDiv.alert('close');
        }, 5000);
    }
    
    return alertDiv;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getCSRFToken,
        makeAuthenticatedRequest,
        showAlert
    };
}
