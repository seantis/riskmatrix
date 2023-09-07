// Adapted from DataTables server side pipelining example
$.fn.dataTable.pipeline = function (ajax_url) {
    var cacheLower = -1;
    var cacheUpper = null;
    var cacheLastRequest = null;
    var cacheLastJson = null;
    var cacheWindowSize = 250;
    var recordsTotal = -1;

    return function(request, drawCallback, settings) {
        var api = new $.fn.dataTable.Api(settings);
        var options = api.init();
        if(recordsTotal < 0 && options.deferLoading) {
            recordsTotal = options.deferLoading;
        }

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
        if(recordsTotal > 0 && requestEnd > recordsTotal) {
            // snap cache window to end
            requestStart -= requestEnd - recordsTotal;
            if(requestStart < 0) {
                requestStart = 0;
            }
            requestEnd = recordsTotal;
        }

        if(settings.clearCache) {
            ajax = true;
            settings.clearCache = false;
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
                    recordsTotal = json.recordsTotal;
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

$.fn.dataTable.Api.register('clearPipeline()', function() {
    return this.iterator('table', function(settings) {
        settings.clearCache = true;
    });
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
    });
});
