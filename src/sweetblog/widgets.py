from django import forms
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.templatetags.static import static
import json


class MarkdownWidget(forms.Textarea):
    """
    A Django form widget that provides a split-pane markdown editor with live preview.
    Features:
    - Live preview with debounced updates via API
    - Auto-refresh every 10 seconds
    - Support for multiple widgets on the same page
    - Server-side rendering using mistune
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'markdown-editor-textarea',
            'rows': 20,
            'cols': 40
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        
        # Ensure unique ID for the widget
        if 'id' not in attrs:
            attrs['id'] = f'id_{name}'
        
        widget_id = attrs['id']
        
        # Render the base textarea
        textarea_html = super().render(name, value, attrs, renderer)
        
        # Get the API URL and CSS file
        api_url = reverse('sweetblog-mistune_api')
        github_css_url = static('sweetblog/github/github-markdown.css')
        
        html = f'''
        <link rel="stylesheet" href="{github_css_url}">
        <div class="markdown-widget-wrapper" id="wrapper-{widget_id}" style="width: 100%;">
            <style>
                #wrapper-{widget_id} {{
                    display: flex;
                    gap: 20px;
                    margin-bottom: 20px;
                    width: 100%;
                }}
                #wrapper-{widget_id} .markdown-editor-container,
                #wrapper-{widget_id} .markdown-preview-container {{
                    flex: 1;
                    min-width: 0;
                    width: 50%;
                }}
                #wrapper-{widget_id} .markdown-editor-textarea {{
                    width: 100%;
                    min-height: 400px;
                    font-family: monospace;
                    font-size: 14px;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    resize: vertical;
                    box-sizing: border-box;
                }}
                #wrapper-{widget_id} .markdown-preview {{
                    min-height: 400px;
                    padding: 16px;
                    border: 1px solid #d1d9e0;
                    border-radius: 6px;
                    background-color: #ffffff;
                    overflow-y: auto;
                    max-height: 600px;
                    box-sizing: border-box;
                }}
                #wrapper-{widget_id} .widget-label {{
                    font-weight: bold;
                    margin-bottom: 8px;
                    display: block;
                    color: #000000;
                }}
                #wrapper-{widget_id} .preview-error {{
                    color: #d1242f;
                    padding: 10px;
                }}
                #wrapper-{widget_id} .preview-loading {{
                    color: #656d76;
                    padding: 10px;
                    font-style: italic;
                }}
                
            </style>
            
            <div class="markdown-editor-container">
                <label class="widget-label">Markdown Editor</label>
                {textarea_html}
            </div>
            
            <div class="markdown-preview-container ">
                <label class="widget-label">Preview</label>
                <div id="preview-{widget_id}" class="markdown-preview markdown-body">
                    <p class="preview-loading">Loading preview...</p>
                </div>
            </div>
            
            <script>
            (function() {{
                'use strict';
                
                const textarea = document.getElementById('{widget_id}');
                const preview = document.getElementById('preview-{widget_id}');
                const apiUrl = '{api_url}';
                let updateTimer = null;
                
                if (!textarea || !preview) {{
                    console.error('Markdown widget elements not found');
                    return;
                }}
                
                // Function to get CSRF token
                function getCookie(name) {{
                    let cookieValue = null;
                    if (document.cookie && document.cookie !== '') {{
                        const cookies = document.cookie.split(';');
                        for (let i = 0; i < cookies.length; i++) {{
                            const cookie = cookies[i].trim();
                            if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                break;
                            }}
                        }}
                    }}
                    return cookieValue;
                }}
                
                // Function to update preview
                function updatePreview() {{
                    const content = textarea.value;
                    
                    if (!content) {{
                        preview.innerHTML = '<p style="color: #999;">Preview will appear here...</p>';
                        return;
                    }}
                    
                    // Show loading state
                    preview.innerHTML = '<p class="preview-loading">Updating preview...</p>';
                    
                    // Send request to API
                    fetch(apiUrl, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        }},
                        body: JSON.stringify({{
                            content: content
                        }})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            preview.innerHTML = data.html;
                        }} else {{
                            preview.innerHTML = '<p class="preview-error">Error: ' + (data.message || 'Unknown error') + '</p>';
                        }}
                    }})
                    .catch(error => {{
                        console.error('Error updating preview:', error);
                        preview.innerHTML = '<p class="preview-error">Error updating preview</p>';
                    }});
                }}
                
                // Debounced update
                function debouncedUpdate() {{
                    clearTimeout(updateTimer);
                    updateTimer = setTimeout(updatePreview, 3000);
                }}
                
                // Event listeners
                textarea.addEventListener('input', debouncedUpdate);
                textarea.addEventListener('change', debouncedUpdate);
                
                // Initial render
                updatePreview();
                
                // Cleanup on page unload
                window.addEventListener('beforeunload', function() {{
                    if (updateTimer) {{
                        clearTimeout(updateTimer);
                    }}
                }});
            }})();
            </script>
        </div>
        '''
        
        return mark_safe(html)