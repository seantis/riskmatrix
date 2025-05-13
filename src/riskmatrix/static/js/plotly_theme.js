// Function to update Plotly theme based on current site theme
function updatePlotlyTheme(theme) {
    const plots = document.querySelectorAll('.js-plotly-plot');
    const isDark = theme === 'dark';
    const textColor = isDark ? '#ffffff' : '#000000';
    
    plots.forEach(plot => {
        if (plot._fullLayout) {
            const update = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                modebar: {
                    bgcolor: 'rgba(0,0,0,0)',
                    color: textColor
                },
                font: { 
                    color: textColor,
                    family: 'DM Sans, sans-serif'
                }
            };

            if (plot._fullLayout.annotations) {
                update.annotations = plot._fullLayout.annotations.map(ann => ({
                    ...ann,
                    font: { 
                        ...ann.font,
                        color: isDark ? '#ffffff' : '#000000',
                        family: 'DM Sans, sans-serif'
                    }
                }));
            }

            if (plot._fullLayout.shapes) {
                update.shapes = plot._fullLayout.shapes.map(shape => ({
                    ...shape,
                    line: { 
                        ...shape.line,
                        color: 'rgba(255,255,255,0.5)'
                    }
                }));
            }

            Plotly.relayout(plot, update);

            if (plot._fullData) {
                const traceUpdate = {
                    'textfont.color': isDark ? '#000000' : '#ffffff',
                    'textfont.family': 'DM Sans, sans-serif',
                    'hoverlabel.font.color': isDark ? '#000000' : '#ffffff',
                    'hoverlabel.bgcolor': isDark ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.9)',
                    'hoverlabel.font.family': 'DM Sans, sans-serif',
                    'marker.color': isDark ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.8)'
                };

                plot._fullData.forEach((trace, i) => {
                    Plotly.restyle(plot, traceUpdate, [i]);
                });
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    updatePlotlyTheme(currentTheme);

    document.documentElement.addEventListener('bs-theme-changed', (e) => {
        updatePlotlyTheme(e.detail.theme);
    });

    document.querySelectorAll('[data-bs-theme-value]').forEach(toggle => {
        toggle.addEventListener('click', () => {
            setTimeout(() => {
                const theme = document.documentElement.getAttribute('data-bs-theme');
                updatePlotlyTheme(theme);
            }, 0);
        });
    });
}); 
