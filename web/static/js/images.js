/**
 * Docker Images Management JavaScript
 * Handles the functionality for the Docker Images page
 */

$(document).ready(function() {
    // Initialize DataTable for local images
    const imagesTable = $('#imagesTable').DataTable({
        ajax: {
            url: '/api/images',
            dataSrc: 'data',
            error: handleAjaxError('Error loading images')
        },
        columns: [
            { data: 'id', width: '15%' },
            { 
                data: 'tags',
                render: renderTags,
                width: '35%'
            },
            { 
                data: 'size_mb',
                render: sizeRenderer,
                width: '15%'
            },
            { 
                data: 'created',
                width: '20%'
            },
            {
                data: 'id',
                orderable: false,
                render: actionButtonsRenderer,
                width: '15%'
            }
        ],
        order: [[2, 'desc']], // Sort by size by default
        responsive: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]]
    });

    // Initialize event listeners
    initEventListeners(imagesTable);
});

/**
 * Render tags as badges
 */
function renderTags(data, type, row) {
    if (!data || !data.length) return '<span class="text-muted">&lt;none&gt;</span>';
    return data.map(tag => 
        `<span class="badge bg-secondary me-1 mb-1">${tag}</span>`
    ).join('');
}

/**
 * Format size with MB unit
 */
function sizeRenderer(data, type, row) {
    return `${data} MB`;
}

/**
 * Render action buttons for each image
 */
function actionButtonsRenderer(data, type, row) {
    return `
        <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-info btn-sm view-image" 
                    data-id="${data}" 
                    title="View Details">
                <i class="fas fa-eye"></i>
            </button>
            <button class="btn btn-outline-danger btn-sm delete-image" 
                    data-id="${data}"
                    data-tags="${row.tags ? row.tags.join(',') : ''}"
                    title="Remove Image">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
}

/**
 * Initialize all event listeners
 */
function initEventListeners(imagesTable) {
    // Search local images
    $('#imageSearch').on('keyup', function() {
        imagesTable.search(this.value).draw();
    });

    // Refresh images
    $('#refreshImagesBtn').on('click', function() {
        imagesTable.ajax.reload();
        showToast('Images refreshed', 'success');
    });

    // Search Docker Hub
    initDockerHubSearch();
    
    // Image operations
    initImageOperations(imagesTable);
}

/**
 * Initialize Docker Hub search functionality
 */
function initDockerHubSearch() {
    const searchHandler = function(e) {
        if (e.which === 13 || $(this).is('button')) {
            const query = $('#dockerHubSearch').val().trim();
            if (!query) return;
            
            const $btn = $('#searchDockerHubBtn');
            const $icon = $btn.find('i');
            const $results = $('#dockerHubResults');
            const $resultsBody = $('#dockerHubResultsBody');
            
            $btn.prop('disabled', true);
            $icon.removeClass('fa-search').addClass('fa-spinner fa-spin');
            
            $.get('/api/images/search', { q: query })
                .done(function(response) {
                    if (response.status === 'success') {
                        $resultsBody.empty();
                        
                        if (response.data && response.data.length > 0) {
                            response.data.forEach(function(image) {
                                const row = `
                                    <tr>
                                        <td>${image.name}</td>
                                        <td>${image.description || '<span class="text-muted">No description</span>'}</td>
                                        <td>${image.stars} <i class="fas fa-star text-warning"></i></td>
                                        <td>${image.official ? '<span class="badge bg-success">Official</span>' : ''}</td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-primary pull-image" 
                                                    data-image="${image.name}">
                                                <i class="fas fa-download me-1"></i> Pull
                                            </button>
                                        </td>
                                    </tr>
                                `;
                                $resultsBody.append(row);
                            });
                            $results.removeClass('d-none');
                        } else {
                            $resultsBody.html('<tr><td colspan="5" class="text-center">No results found</td></tr>');
                            $results.removeClass('d-none');
                        }
                    } else {
                        showToast(response.message || 'Error searching Docker Hub', 'danger');
                    }
                })
                .fail(handleAjaxError('Error searching Docker Hub'))
                .always(function() {
                    $btn.prop('disabled', false);
                    $icon.removeClass('fa-spinner fa-spin').addClass('fa-search');
                });
        }
    };
    
    $('#searchDockerHubBtn, #dockerHubSearch').on('keypress', searchHandler);
    
    // Close Docker Hub results
    $('#closeDockerHubResults').on('click', function() {
        $('#dockerHubResults').addClass('d-none');
    });
    
    // Pull image from Docker Hub results
    $(document).on('click', '.pull-image', function() {
        const imageName = $(this).data('image');
        $('#imageName').val(imageName);
        $('#pullImageModal').modal('show');
    });
}

/**
 * Initialize image operations (pull, view, delete)
 */
function initImageOperations(imagesTable) {
    // Pull image from form
    $('#pullImageBtn').on('click', function() {
        const $btn = $(this);
        const $form = $('#pullImageForm');
        const $progress = $('#pullProgress');
        const $status = $('#pullStatus');
        
        if (!form.checkValidity()) {
            $form.addClass('was-validated');
            return;
        }
        
        const imageName = $('#imageName').val().trim();
        const imageTag = $('#imageTag').val().trim() || 'latest';
        const fullImage = imageTag ? `${imageName}:${imageTag}` : imageName;
        
        $btn.prop('disabled', true);
        $status.html(`<i class="fas fa-spinner fa-spin"></i> Pulling ${fullImage}...`);
        $progress.removeClass('d-none').find('.progress-bar').css('width', '0%');
        
        // Start pulling the image
        $.ajax({
            url: '/api/images/pull',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                image: imageName,
                tag: imageTag
            }),
            success: function(response) {
                if (response.status === 'pending') {
                    // Poll for completion
                    const pollInterval = setInterval(function() {
                        imagesTable.ajax.reload(function() {
                            // Check if the image was pulled successfully
                            const imageExists = imagesTable.rows().data().toArray()
                                .some(img => img.tags && img.tags.includes(fullImage));
                            
                            if (imageExists) {
                                clearInterval(pollInterval);
                                $status.html(`<span class="text-success"><i class="fas fa-check-circle"></i> Successfully pulled ${fullImage}</span>`);
                                $btn.prop('disabled', false);
                                showToast(`Successfully pulled ${fullImage}`, 'success');
                            }
                        });
                    }, 2000);
                    
                    // Timeout after 5 minutes
                    setTimeout(function() {
                        clearInterval(pollInterval);
                        $status.html(`<span class="text-warning"><i class="fas fa-exclamation-triangle"></i> Pull timed out. Check server logs for details.</span>`);
                        $btn.prop('disabled', false);
                    }, 300000);
                    
                    // Close modal after a short delay
                    setTimeout(function() {
                        $('#pullImageModal').modal('hide');
                        // Reset form after modal is hidden
                        $('#pullImageModal').on('hidden.bs.modal', function() {
                            $form[0].reset();
                            $form.removeClass('was-validated');
                            $progress.addClass('d-none');
                            $status.empty();
                        });
                    }, 2000);
                }
            },
            error: handleAjaxError('Failed to pull image', $status, $btn)
        });
    });

    // View image details
    $(document).on('click', '.view-image', function() {
        const imageId = $(this).data('id');
        const $modal = $('#imageDetailsModal');
        const $modalBody = $('#imageDetailsBody');
        
        $modalBody.html(`
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading image details...</p>
            </div>
        `);
        
        $modal.modal('show');
        
        // Get image details
        $.get(`/api/images/${imageId}`)
            .done(function(response) {
                if (response.status === 'success') {
                    renderImageDetails(response.data, $modalBody);
                } else {
                    $modalBody.html(`
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            ${response.message || 'Failed to load image details'}
                        </div>
                    `);
                }
            })
            .fail(handleAjaxError('Error loading image details', $modalBody));
    });

    // Delete image
    $(document).on('click', '.delete-image', function() {
        const imageId = $(this).data('id');
        const imageTags = $(this).data('tags') || 'untagged image';
        
        bootbox.confirm({
            title: '<i class="fas fa-exclamation-triangle text-danger me-2"></i>Confirm Deletion',
            message: `Are you sure you want to remove the following image?<br><br>
                     <strong>ID:</strong> ${imageId}<br>
                     <strong>Tags:</strong> ${imageTags || '<span class="text-muted">&lt;none&gt;</span>'}`,
            buttons: {
                confirm: {
                    label: 'Yes, remove it',
                    className: 'btn-danger'
                },
                cancel: {
                    label: 'Cancel',
                    className: 'btn-secondary'
                }
            },
            callback: function(result) {
                if (result) {
                    $.ajax({
                        url: `/api/images/${imageId}/remove`,
                        method: 'DELETE',
                        success: function(response) {
                            if (response.status === 'success') {
                                showToast('Image removed successfully', 'success');
                                imagesTable.ajax.reload();
                            } else {
                                showToast(response.message || 'Failed to remove image', 'danger');
                            }
                        },
                        error: handleAjaxError('Error removing image')
                    });
                }
            }
        });
    });
}

/**
 * Render image details in the modal
 */
function renderImageDetails(image, $container) {
    let html = `
        <div class="row">
            <div class="col-md-4 fw-bold">ID:</div>
            <div class="col-md-8">
                <code>${image.id}</code>
                <button class="btn btn-sm btn-outline-secondary ms-2 copy-btn" 
                        data-bs-toggle="tooltip" 
                        title="Copy to clipboard"
                        data-clipboard-text="${image.id}">
                    <i class="far fa-copy"></i>
                </button>
            </div>
            
            <div class="col-md-4 fw-bold mt-2">Tags:</div>
            <div class="col-md-8 mt-2">
                ${image.tags && image.tags.length ? 
                    image.tags.map(tag => 
                        `<span class="badge bg-secondary me-1 mb-1">${tag}</span>`
                    ).join('') : 
                    '<span class="text-muted">&lt;none&gt;</span>'
                }
            </div>
            
            <div class="col-md-4 fw-bold mt-2">Size:</div>
            <div class="col-md-8 mt-2">${image.size_mb} MB</div>
            
            <div class="col-md-4 fw-bold mt-2">Virtual Size:</div>
            <div class="col-md-8 mt-2">${image.virtual_size} MB</div>
            
            <div class="col-md-4 fw-bold mt-2">Created:</div>
            <div class="col-md-8 mt-2">${image.created}</div>
            
            <div class="col-md-4 fw-bold mt-2">Labels:</div>
            <div class="col-md-8 mt-2">
    `;
    
    if (image.labels && Object.keys(image.labels).length > 0) {
        html += '<div class="table-responsive"><table class="table table-sm table-bordered">';
        for (const [key, value] of Object.entries(image.labels)) {
            html += `
                <tr>
                    <th style="width: 30%;">${key}</th>
                    <td>${value}</td>
                </tr>
            `;
        }
        html += '</table></div>';
    } else {
        html += '<span class="text-muted">No labels</span>';
    }
    
    html += '</div></div>';
    $container.html(html);
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Initialize clipboard.js
    new ClipboardJS('.copy-btn');
}

/**
 * Handle AJAX errors consistently
 */
function handleAjaxError(defaultMessage, $statusElement, $buttonElement) {
    return function(xhr) {
        const error = xhr.responseJSON || {};
        const message = error.message || defaultMessage || 'An error occurred';
        
        if ($statusElement) {
            $statusElement.html(`<span class="text-danger"><i class="fas fa-times-circle"></i> ${message}</span>`);
        } else {
            showToast(message, 'danger');
        }
        
        if ($buttonElement) {
            $buttonElement.prop('disabled', false);
        }
        
        console.error(message, error);
    };
}
