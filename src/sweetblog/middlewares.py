from django.utils.deprecation import MiddlewareMixin
from crawlerdetect import CrawlerDetect
from .models import Device
import uuid


class DeviceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip admin paths
        if request.path.startswith('/admin/'):
            return None
        
        # Initialize crawler detector
        crawler_detect = CrawlerDetect()
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Skip if request is from a crawler/bot
        if crawler_detect.isCrawler(user_agent):
            return None
        
        # Check for existing device_uuid cookie
        device_uuid = request.COOKIES.get('device_uuid')

        if device_uuid:
            try:
                # Try to fetch existing device
                device = Device.objects.get(uuid=device_uuid)
                if request.user.is_authenticated and device.user != request.user:
                    device.user = request.user
                    device.save()
                elif device.user:
                    request.user = device.user

                request.device = device
            except (Device.DoesNotExist, ValueError):
                # Create new device if not found or invalid UUID
                device = Device.from_request(request)
                request.device = device
        else:
            # No cookie found, create new device
            device = Device.from_request(request)
            request.device = device
        
        return None
    
    def process_response(self, request, response):
        # Skip admin paths
        if request.path.startswith('/admin/'):
            return response
            
        # Skip if request is from a crawler/bot
        crawler_detect = CrawlerDetect()
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if crawler_detect.isCrawler(user_agent):
            return response
        
        # Set device_uuid cookie if device exists on request
        if hasattr(request, 'device') and request.device:
            response.set_cookie('device_uuid', str(request.device.uuid))
        
        return response