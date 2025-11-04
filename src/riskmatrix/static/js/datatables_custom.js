// we add some additional settings for caching
$.fn.dataTable.models.oSettings.oCache = {
    recordsTotal: -1,
    clear: false,
}

// Adapted from DataTables server side pipelining example
$.fn.dataTable.pipeline = function (ajax_url) {
    var cacheLower = -1;
    var cacheUpper = null;
    var cacheLastRequest = null;
    var cacheLastJson = null;
    var cacheWindowSize = 250;

    return function(request, drawCallback, settings) {
        var api = new $.fn.dataTable.Api(settings);
        api.initCache();

        var ajax          = false;
        var drawStart     = request.start;
        var drawLength    = request.length;
        var drawEnd       = request.start + request.length;
        var cacheMargin   = cacheWindowSize - request.length;
        if(cacheMargin < 0) {
            cacheMargin = 0;
        } else if(request.length > 0 && cacheMargin < 2*request.length) {
            // cache at least one full page to either side
            cacheMargin = 2*request.length;
        }
        var requestStart  = drawStart - cacheMargin/2;
        var requestEnd    = drawEnd + cacheMargin/2;
        if(requestStart < 0) {
            // snap cache window to start
            requestEnd -= requestStart;
            requestStart = 0;
        }
        if(settings.oCache.recordsTotal > 0 && requestEnd > settings.oCache.recordsTotal) {
            // snap cache window to end
            requestStart -= requestEnd - settings.oCache.recordsTotal;
            if(requestStart < 0) {
                requestStart = 0;
            }
            requestEnd = settings.oCache.recordsTotal;
        }

        if(settings.oCache.clear) {
            ajax = true;
            settings.oCache.clear = false;
        } else if(drawLength < 0) {
            ajax = true;
        } else if(cacheLower < 0 || drawStart < cacheLower || drawEnd > cacheUpper) {
            ajax = true;
        } else if(
            JSON.stringify(request.order)   !== JSON.stringify(cacheLastRequest.order) ||
            JSON.stringify(request.columns) !== JSON.stringify(cacheLastRequest.columns) ||
            JSON.stringify(request.search)  !== JSON.stringify(cacheLastRequest.search)
        ) {
            ajax = true;
        }

        cacheLastRequest = $.extend(true, {}, request);
        if(ajax) {
            cacheLower = requestStart;
            cacheUpper = requestEnd;
            request.start = requestStart;
            if(drawLength > 0) {
                request.length = requestEnd - requestStart;
            }

            return $.ajax({
                'type': 'GET',
                'url': ajax_url,
                'data': request,
                'dataType': 'json',
                'cache': false,
                'success': function(json) {
                    settings.oCache.recordsTotal = json.recordsTotal;
                    cacheLastJson = $.extend(true, {}, json);
                    if(cacheLower != drawStart) {
                        json.data.splice(0, drawStart-cacheLower);
                    }
                    if(drawLength >= -1) {
                        json.data.splice(drawLength, json.data.length);
                    }
                    drawCallback(json);
                }
            });
        } else {
            json = $.extend(true, {}, cacheLastJson);
            json.draw = request.draw;
            json.data.splice(0, drawStart-cacheLower);
            json.data.splice(drawLength, json.data.length);
            drawCallback(json);
        }
    }
};

$.fn.dataTable.Api.register('initCache()', function() {
    var options = this.init();
    return this.iterator('table', function(settings) {
        if(settings.oCache.recordsTotal < 0 && options.deferLoading) {
            settings.oCache.recordsTotal = options.deferLoading;
        }
    });
});

$.fn.dataTable.Api.register('clearPipeline()', function() {
    return this.iterator('table', function(settings) {
        settings.oCache.clear = true;
    });
});

// compared to the normal add this will make sure server-side-processing
// will perform a full refetch, rather than a truncated one to the old
// size of the result-set
// TODO: We could improve this by modifying the XHR cache in-place, rather
//       than always doing a refetch
$.fn.dataTable.Api.register('row.add_xhr()', function(row) {
    this.initCache();
    this.iterator('table', function(settings) {
        if (settings._iRecordsDisplay >= 0) {
            settings._iRecordsDisplay++;
        }
        settings.oCache.recordsTotal++;
        settings.oCache.clear = true;
    });
    return this.row.add(row);
});

$.fn.dataTable.Api.register('rows.add_xhr()', function(rows) {
    this.initCache();
    this.iterator('table', function(settings) {
        for (var i=0; i<rows.length; i++) {
            if (settings._iRecordsDisplay >= 0) {
                settings._iRecordsDisplay++;
            }
            settings.oCache.recordsTotal++;
        }
        settings.oCache.clear = true;
    });
    return this.rows.add(rows);
});

$(function() {
    function popover(element, message, type) {
        var popover = new bootstrap.Popover(element, {
            content: message,
            placement: 'top',
            container: 'body',
            template: '<div class="popover border-'+type+'" role="tooltip"><div class="popover-arrow"></div><div class="popover-body text-'+type+'"></div></div>',
            trigger: 'custom',
        });

        popover.show();

        $(element).one('focusout', function() { popover.dispose(); });
    }

    $('.data-table').each(function(index, element) {
        var opts = {};
        var table = $(element);
        var ajax_url = table.data('ajax');
        if(ajax_url) {
            table.removeAttr('data-ajax').removeData('ajax');
            opts.ajax = $.fn.dataTable.pipeline(ajax_url);
        }
        table = table.DataTable(opts);
        table.on('click', '.remove-row', function(event) {
            event.preventDefault();
            var button = $(this);
            var incr_counter = button.data('increment-counter');
            var decr_counter = button.data('decrement-counter');
            var row = table.row($(this).closest('tr'));
            var target = $(this).attr('href');
            $.get(target, function(data) {
                var tooltip = bootstrap.Tooltip.getInstance(button.children('span')[0]);
                if(tooltip) {
                    tooltip.disable();
                    tooltip.hide();
                }
                row.remove().draw();

                if(incr_counter) {
                    var counter = $('#'+incr_counter);
                    var count = parseInt(counter.text());
                    if(!isNaN(count)) {
                        count++;
                        counter.text(count);
                    }
                }

                if(decr_counter) {
                    var counter = $('#'+decr_counter);
                    var count = parseInt(counter.text());
                    if(!isNaN(count)) {
                        count--;
                        counter.text(count);
                    }
                }
            });
            return false;
        });
        table.on('click', '.remove-button', function(event) {
            event.preventDefault();
            var button = $(this);
            var row = table.row($(this).closest('tr'));
            var target = $(this).attr('href');
            $.get(target, function(data) {
                var row_data = row.data();
                if(data['error'] !== undefined) {
                    popover(button[0], data['error'], 'danger');
                    return;
                }
                $.each(data, function(index, column) {
                    row_data[column['index']] = column['value'];
                });
                var cell = button.parent();
                var tooltip = bootstrap.Tooltip.getInstance(button.children('span')[0]);
                tooltip.disable();
                tooltip.hide();
                button.remove();
                row_data['buttons'] = cell.html();
                row.data(row_data);
            });
            return false;
        });
        table.on('change', '.form-check-input', function(event) {
            var target = $(this).attr('data-url')
            var csrf_token = $(this).attr('data-csrf_token')
            $.ajax({
                url: target,
                type: 'PUT',
                headers: {'X-CSRF-Token': csrf_token},
            });
        });
    });
});

// Treatment form handling
document.addEventListener('DOMContentLoaded', function() {
    // Handle URL parameter for open accordion
    const urlParams = new URLSearchParams(window.location.search);
    const openRiskId = urlParams.get('risk');
    if (openRiskId) {
        const accordion = document.querySelector(`#collapse-${openRiskId}`);
        if (accordion) {
            accordion.classList.add('show');
            const button = document.querySelector(`#heading-${openRiskId} .accordion-button`);
            if (button) {
                button.classList.remove('collapsed');
                button.setAttribute('aria-expanded', 'true');
            }
        }
    }

    // Update URL when accordion is toggled
    document.querySelector('#treatmentAccordion').addEventListener('shown.bs.collapse', function(e) {
        // When an accordion is shown, update URL with its risk ID
        const riskId = e.target.id.replace('collapse-', '');
        const url = new URL(window.location);
        url.searchParams.set('risk', riskId);
        window.history.pushState({}, '', url);
    });

    document.querySelector('#treatmentAccordion').addEventListener('hidden.bs.collapse', function(e) {
        // When an accordion is hidden, remove the risk ID from URL
        const url = new URL(window.location);
        url.searchParams.delete('risk');
        window.history.pushState({}, '', url);
    });

    function submitForm(form) {
        const formData = new FormData(form);
        const csrfToken = form.querySelector('input[name="csrf_token"]').value;
        
        return fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'same-origin'
        }).then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        }).then(data => {
            if (data.errors) {
                console.error('Validation errors:', data.errors);
                // Show error feedback
                const errorDiv = form.querySelector('.alert-danger') || document.createElement('div');
                errorDiv.className = 'alert alert-danger mt-2';
                errorDiv.textContent = Object.values(data.errors).flat().join(', ');
                if (!form.querySelector('.alert-danger')) {
                    form.insertBefore(errorDiv, form.firstChild);
                }
                return data;
            }

            // Clear any error messages
            const errorDiv = form.querySelector('.alert-danger');
            if (errorDiv) {
                errorDiv.remove();
            }

            // Update the treatment type if provided
            if (data.treatment_type) {
                const treatmentSelect = form.querySelector('.treatment-select');
                if (treatmentSelect) {
                    // Update the button text
                    const buttonText = treatmentSelect.querySelector('.treatment-button span');
                    if (buttonText) {
                        buttonText.textContent = data.treatment_type;
                    }

                    // Update the selected state in options
                    const options = treatmentSelect.querySelectorAll('.treatment-option');
                    options.forEach(option => {
                        const isSelected = option.getAttribute('data-value') === data.treatment_type.toUpperCase();
                        option.classList.toggle('selected', isSelected);
                    });

                    // Update the header treatment type
                    const accordionItem = form.closest('.accordion-item');
                    const header = accordionItem.querySelector('.accordion-button .row');
                    const treatmentTypeCell = header.querySelector('.col-4:last-child');
                    
                    // Create or update the treatment type badge
                    let badge = treatmentTypeCell.querySelector('.treatment-type');
                    if (!badge) {
                        badge = document.createElement('span');
                        treatmentTypeCell.textContent = ''; // Clear the dash
                        treatmentTypeCell.appendChild(badge);
                    }
                    
                    // Update badge classes and text
                    badge.className = 'treatment-type ' + data.treatment_type.toLowerCase().replace('/', '');
                    badge.textContent = data.treatment_type;
                }
            }

            // Show/hide post-treatment fields if treatment type changes
            const postTreatmentFields = form.querySelectorAll('.post-treatment-fields');
            postTreatmentFields.forEach(field => {
                if (data.treatment_type === 'Reduce') {
                    field.style.display = 'block';
                } else {
                    field.style.display = 'none';
                }
            });

            return data;
        }).catch(error => {
            console.error('Error:', error);
            // Show error feedback
            const errorDiv = form.querySelector('.alert-danger') || document.createElement('div');
            errorDiv.className = 'alert alert-danger mt-2';
            errorDiv.textContent = 'Error saving changes: ' + error.message;
            if (!form.querySelector('.alert-danger')) {
                form.insertBefore(errorDiv, form.firstChild);
            }
            throw error;
        });
    }

    // Auto-save functionality for fields with data-autosave="true"
    document.querySelectorAll('[data-autosave="true"]').forEach(function(element) {
        element.addEventListener('change', function() {
            const form = this.closest('form');
            submitForm(form);
        });
    });

    // Handle treatment type selection
    document.querySelectorAll('select[name="treatment_type"]').forEach(function(select) {
        select.addEventListener('change', function() {
            const form = this.closest('form');
            const postTreatmentFields = form.querySelector('.post-treatment-fields');
            
            // Immediately show/hide fields based on selection
            if (this.value === 'REDUCE') {
                postTreatmentFields.style.display = 'block';
            } else {
                postTreatmentFields.style.display = 'none';
            }
            
            submitForm(form).then(data => {
                if (data && data.success) {
                    // Update display state again in case server response differs
                    if (data.treatment_type === 'Reduce') {
                        postTreatmentFields.style.display = 'block';
                    } else {
                        postTreatmentFields.style.display = 'none';
                    }
                }
            });
        });
    });

    // Save description after user stops typing
    let descriptionTimeout;
    document.querySelectorAll('textarea[name="description"]').forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            clearTimeout(descriptionTimeout);
            const form = this.closest('form');
            descriptionTimeout = setTimeout(function() {
                submitForm(form);
            }, 1000);
        });
    });

    // Links management
    document.querySelectorAll('.add-link').forEach(function(button) {
        button.addEventListener('click', function() {
            const container = this.closest('.links-container');
            const newRow = document.createElement('div');
            newRow.className = 'input-group mb-2';
            newRow.innerHTML = `
                <input type="text" class="form-control" name="links-${container.querySelectorAll('input[type="text"]').length}"
                       placeholder="Add new link..." data-autosave="false"/>
                <button class="btn btn-outline-danger remove-link" type="button">
                    <i class="fa fa-trash"></i>
                </button>
            `;
            container.insertBefore(newRow, this.closest('.input-group'));
        });
    });

    document.addEventListener('click', function(e) {
        const removeButton = e.target.closest('.remove-link');
        if (removeButton) {
            const row = removeButton.closest('.input-group');
            const container = row.closest('.links-container');
            const form = container.closest('form');
            
            row.remove();
            
            // Update indices for remaining links
            container.querySelectorAll('input[type="text"]').forEach((input, index) => {
                input.name = `links-${index}`;
            });
            
            submitForm(form);
        }
    });

    // Save links when input loses focus
    document.addEventListener('focusout', function(e) {
        if (e.target.matches('input[name^="links-"]')) {
            const form = e.target.closest('form');
            submitForm(form);
        }
    });

    // Handle radio button changes for post-treatment values
    document.querySelectorAll('input[type="radio"][name^="post_"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            const form = this.closest('form');
            submitForm(form);
        });
    });

    // Treatment search functionality
    const treatmentSearch = document.querySelector('#treatment-search');
    if (treatmentSearch) {
        treatmentSearch.addEventListener('input', function(e) {
            const searchText = e.target.value.toLowerCase();
            const items = document.querySelectorAll('#treatmentAccordion .accordion-item');
            
            items.forEach(item => {
                const name = item.querySelector('.col-4').textContent.toLowerCase();
                const description = item.querySelector('textarea[name="description"]')?.value.toLowerCase() || '';
                
                if (name.includes(searchText) || description.includes(searchText)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // Treatment dropdown functionality
    document.querySelectorAll('.treatment-select').forEach(function(select) {
        const button = select.querySelector('.treatment-button');
        const options = select.querySelector('.treatment-options');
        const buttonText = button.querySelector('span');

        // Toggle dropdown
        button.addEventListener('click', function(e) {
            const isExpanded = button.getAttribute('aria-expanded') === 'true';
            button.setAttribute('aria-expanded', !isExpanded);
            options.classList.toggle('show');
            
            // Close other dropdowns
            document.querySelectorAll('.treatment-select').forEach(function(otherSelect) {
                if (otherSelect !== select) {
                    const otherButton = otherSelect.querySelector('.treatment-button');
                    const otherOptions = otherSelect.querySelector('.treatment-options');
                    otherButton.setAttribute('aria-expanded', 'false');
                    otherOptions.classList.remove('show');
                }
            });
        });

        // Handle option selection
        options.querySelectorAll('.treatment-option').forEach(function(option) {
            option.addEventListener('click', function() {
                const value = this.getAttribute('data-value');
                const displayText = this.textContent;
                
                // Close dropdown
                button.setAttribute('aria-expanded', 'false');
                options.classList.remove('show');
                
                // Get the form and submit it
                const form = select.closest('form');
                if (form) {
                    // Create a temporary hidden input for the treatment type
                    const tempInput = document.createElement('input');
                    tempInput.type = 'hidden';
                    tempInput.name = 'treatment_type';
                    tempInput.value = value;
                    form.appendChild(tempInput);
                    
                    // Submit the form
                    submitForm(form).then((data) => {
                        // Remove the temporary input after submission
                        form.removeChild(tempInput);
                        
                        if (data && data.success) {
                            // Update the button text and selected state
                            buttonText.textContent = displayText;
                            options.querySelectorAll('.treatment-option').forEach(opt => {
                                const isSelected = opt.getAttribute('data-value') === value;
                                opt.classList.toggle('selected', isSelected);
                            });
                            
                            // Update the header treatment type
                            const accordionItem = form.closest('.accordion-item');
                            const header = accordionItem.querySelector('.accordion-button .row');
                            const treatmentTypeCell = header.querySelector('.col-4:last-child');
                            
                            // Create or update the treatment type badge
                            let badge = treatmentTypeCell.querySelector('.treatment-type');
                            if (!badge) {
                                badge = document.createElement('span');
                                treatmentTypeCell.textContent = ''; // Clear the dash
                                treatmentTypeCell.appendChild(badge);
                            }
                            
                            // Update badge classes and text using the server's response
                            const treatmentType = data.treatment_type;
                            badge.className = 'treatment-type ' + treatmentType.toLowerCase().replace('/', '');
                            badge.textContent = treatmentType;
                            
                            // Show/hide post-treatment fields if treatment type changes
                            const postTreatmentFields = form.querySelectorAll('.post-treatment-fields');
                            postTreatmentFields.forEach(field => {
                                field.style.display = value === 'REDUCE' ? 'block' : 'none';
                            });
                        }
                    });
                }
            });
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!select.contains(e.target)) {
                button.setAttribute('aria-expanded', 'false');
                options.classList.remove('show');
            }
        });
    });
});
