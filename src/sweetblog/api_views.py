from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from sweetblog.utils import markdown


@method_decorator(csrf_exempt, name='dispatch')
class MistuneView(View):
    """
    API view that converts markdown to HTML using mistune
    """
    
    def post(self, request):
        try:
            # Parse JSON body
            data = json.loads(request.body.decode('utf-8'))
            markdown_content = data.get('content', '')
            
            # Convert markdown to HTML using mistune
            html_content = markdown(markdown_content)
            
            return JsonResponse({
                'status': 'success',
                'html': html_content
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON'
            }, status=400)
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)