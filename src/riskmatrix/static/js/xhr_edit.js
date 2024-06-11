$(function() {
    var table = null;
    var active_row = null;
    var active_popover = null;
    var popover_timeout = null;
    function _unescape(string) {
        return string
            .replace(/&gt;/g, '>')
            .replace(/&lt;/g, '<')
            .replace(/&(#39|apos);/g, "'")
            .replace(/&(#34|quot);/g, '"')
            .replace(/&amp;/g, '&')
    }
    function clear_popover() {
        if (popover_timeout !== null) {
            clearTimeout(popover_timeout);
            popover_timeout = null;
        }
        if (active_popover !== null) {
            active_popover.dispose();
            active_popover = null;
        }
    }
    function popover(element, placement, message, type) {
        // dispose the old popover before showing a new one
        clear_popover();
        active_popover = new bootstrap.Popover(element, {
            content: message,
            placement: placement,
            container: 'body',
            template: '<div class="popover border-'+type+'" role="tooltip"><div class="popover-body text-'+type+'"></div></div>',
            trigger: 'custom',
        });

        active_popover.show();
        $(active_popover.tip).click(clear_popover);
        popover_timeout = setTimeout(clear_popover, 3000);
    }
    var fields = $('#edit-xhr-form').data('fields') || [];

    $('#edit-xhr').on('show.bs.modal', function(event) {
        var source = $(event.relatedTarget);
        var edit_url = source.attr('href');

        // remove old validation errors
        $('#edit-xhr-form input')
        .removeClass('is-invalid').remove('.invalid-feedback');

        var table_id = source.data('table-id');
        if (table_id) {
            // add row button
            table = $('#' + table_id).DataTable({'retrieve': true});
            active_row = 'add';
            // clear form fields
            $.each(fields, function(index, name) {
                $('#edit-xhr-'+ name).val('');
            });
        } else {
            // edit row button
            table = source.closest('table').DataTable({'retrieve': true});
            active_row = table.row(source.closest('tr'));
            var row_data = active_row.data();
            $.each(fields, function(index, name) {
                $('#edit-xhr-'+ name).val(_unescape(row_data[name]));
            });
        }

        $('#edit-xhr-form').attr('action', edit_url);
    });

    // focus first form field
    if (fields.length > 0) {
        $('#edit-xhr').on('shown.bs.modal', function(event) {
            $('#edit-xhr-'+ fields[0]).trigger('focus');
        });
    }

    $('#delete-xhr').on('show.bs.modal', function(event) {
        var source = $(event.relatedTarget);
        var title = source.data('item-title');
        var delete_url = source.attr('href');

        table = source.closest('table').DataTable({'retrieve': true});
        active_row = table.row(source.closest('tr'));

        $('#delete-xhr-item-title').text(title);
        $('#delete-xhr .btn-danger').attr('href', delete_url);
    });

    $('#delete-xhr .btn-danger').on('click', function(event) {
        event.preventDefault();
        var btn = $(this);
        var delete_url = btn.attr('href');
        var csrf_token = btn.data('csrf-token');
        $.ajax({
            url: delete_url,
            type: 'DELETE',
            headers: {'X-CSRF-Token': csrf_token},
            dataType: 'json',
            cache: false,
        }).done(function(data) {
            var node = active_row.node();
            var neighbour, placement;
            if (node.nextElementSibling !== null) {
                neighbour = node.nextElementSibling;
                placement = 'top';
            } else if (node.previousElementSibling !== null) {
                neighbour = node.previousElementSibling;
                placement = 'bottom';
            } else {
                neighbour = node.parent;
                placement = 'bottom';
            }
            var neighbour = node.nextElementSibling || node.previousElementSibling;
            popover(neighbour, placement, data['success'], 'success');
            active_row.remove().clearPipeline().draw(false);
        });
        var modal = document.getElementById('delete-xhr');
        bootstrap.Modal.getInstance(modal).hide();
        return false;
    });

    function enable_submits(buttons) {
        if(!buttons.attr('aria-disabled')) {
            return
        }
        buttons.removeClass('disabled');
        buttons.removeAttribute('aria-disabled');
        buttons.each(function(index, element) {
            var btn = new bootstrap.Button(element);
            btn.toggle();
        });
    }

    $('#edit-xhr-form').on('submit', function(event) {
        event.preventDefault();
        var form = $(this);
        var edit_url = form.attr('action');
        var button = form.find('.submit-button');
        $.post(edit_url, form.serialize(), function(data) {
            form.find('input').removeClass('is-invalid');
            form.find('.invalid-feedback').remove();
            if(data['errors']) {
                $.each(data['errors'], function(key, value) {
                    var feedback = $('<div class="invalid-feedback"></div>').text(value);
                    var field = $('#edit-xhr-'+key);
                    field.addClass('is-invalid').parent().append(feedback);
                });
                enable_submits(button);
            } else {
                if (active_row === 'add') {
                    // add a new row
                    var row_data = {};
                    $.each(fields, function(index, name) {
                        row_data[name] = data[name];
                    });
                    row_data['buttons'] = data['buttons'];
                    row_data['DT_RowId'] = data['DT_RowId'];

                    // drawing could be deferred so we need an event handler
                    // to respond to the newly added row being drawn once
                    table.one('draw', function() {
                        var node = document.getElementById(data['DT_RowId']);
                        // have a sane fallback if the row doesn't exist, because
                        // it e.g. scrolled past the end of the page
                        if(node === null) {
                            var nodes = table.rows({page: 'current'}).nodes();
                            if(nodes.length === 0) {
                                node = table.table().body();
                            } else {
                                node = nodes[Math.ceil(nodes.length/2)];
                            }
                        }
                        popover(node, 'top', data['message'], 'success');
                    });
                    table.row.add_xhr(row_data).draw(false);
                } else {
                    // edit existing row
                    var row_data = active_row.data();
                    $.each(fields, function(index, name) {
                        row_data[name] = data[name];
                    });
                    active_row.data(row_data);
                }
                var modal = document.getElementById('edit-xhr');
                bootstrap.Modal.getInstance(modal).hide();

                // reset the active row and table
                table = null;
                active_row = null;
            }
        });
        return false;
    });
});

$(document).ready(function () {
    marked.use({
        hooks: {
            postprocess: function (html) {
                return html.replace(/\sdisabled=""/g, '');
            }
        }
    });

    var risks_modal = $("form#generate-risks-xhr-form");

    if (risks_modal.length === 0) return;
    risks_modal = risks_modal[0];
    $('div.modal#generate-risks-xhr').modal('show');

    $('div.modal#generate-risks-xhr').on('hidden.bs.modal', function (e) {
        window.location.href = '/risk_catalog';
    })

    var answers = JSON.parse(risks_modal.dataset.answers);
    var catalogs = JSON.parse(risks_modal.dataset.catalogs);
    var idx = 0;
    var csrf_token = $("#generate-risks")[0].dataset['csrfToken'];
    var title = $("h5#generate-risks-xhr-title").first();
    var save_button = $("button#generate-risks")[0];
    title.text(catalogs[idx].title);

    function initiateGeneration(catalog) {
        console.log(catalog)
        console.log("Fetching data...");
        title.text("Generating risks for '" + catalog.name + "' catalog..");
        // Initialize a variable to accumulate received text
        let accumulatedText = '';

        // Function to update the modal body with new text
        function updateModalBody(newText) {
            // Remove all contents from div.modal-body
            $("#generate-risks-xhr div.modal-body").empty();
            const htmlContent = marked.parse(newText, { gfm: true });
            // Insert the parsed HTML into div.modal-body
            $("#generate-risks-xhr div.modal-body").html(htmlContent);
        }

        // Using the Fetch API to handle the streaming response
        fetch('/risk_catalog/generate/stream', {
            method: 'POST',
            headers: {
                'X-CSRF-Token': csrf_token,
                'X-Requested-With': 'XMLHttpRequest' // Mark the request as an AJAX request
            },
            body: JSON.stringify({
                answers,
                catalog
            }),
        }).then(response => {
            updateModalBody('Awaiting magician response...')
            save_button.disabled = true;
            const reader = response.body.getReader();

            // Function to process the stream
            (async function readStream() {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    let textChunk = new TextDecoder("utf-8").decode(value);
                    accumulatedText += textChunk; // Accumulate the new text chunk
                    updateModalBody(accumulatedText); // Update the modal body with the new accumulated text
                }
                save_button.disabled = false;
                title.text("Generated Risks for '" + catalog.name + "' catalog");
            })();
        }).catch(error => {
            console.error("Error fetching data:", error);
        });



    }
    $("button#generate-risks").on('click', function (event) {
        event.preventDefault();
        // Array to hold the objects
        var risks = [];

        $(this).disabled = true;

        // Iterate over each list item
        $('#generate-risks-xhr div.modal-body ul > li').each(function () {
            // For each 'li', find the 'input' (checkbox) and check its checked status
            var isChecked = $(this).find('input[type="checkbox"]').is(':checked');

            // Extract the risk name from the 'strong' element
            var name = $(this).find('strong').text();

            // Extract the description by getting the entire text of 'li'
            // and then removing the name (including the following colon and space).
            var description = $(this).text().replace(name + ': ', '');
            if (isChecked) {
                // Construct the risk object and add it to the 'risks' array
                risks.push({
                    name: name,
                    description: description,
                    catalog: catalogs[idx],
                });
            }
        });


        Promise.all(risks.map(risk => {


            // make post request to /risk_catalog/{id}/add
            return fetch('/risks_catalog/' + catalogs[idx].id + '/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrf_token,
                    'X-Requested-With': 'XMLHttpRequest' // Mark the request as an AJAX request
                },
                body: JSON.stringify(risk),
            }).then(response => {
                return response.json();
            }).then(data => {
                risks = [];
            }).catch(error => {
                console.error("Error fetching data:", error);
            }).finally(() => {
            });
        })).then(() => {
            idx += 1;
            if (idx >= catalogs.length) {
                console.log("No more catalogs to process");
                $('div.modal#generate-risks-xhr').modal('hide');
                return;
            }
            initiateGeneration(catalogs[idx]);
        })



    });


    initiateGeneration(catalogs[idx]);
});
