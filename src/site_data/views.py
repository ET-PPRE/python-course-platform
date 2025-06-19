import os
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def tinymce_image_upload(request):
    if request.method == "POST":
        image = request.FILES.get("file")
        if not image:
            return JsonResponse({"error": "No image uploaded"}, status=400)

        filename = f"{uuid.uuid4().hex}_{image.name}"
        upload_path = os.path.join("tinymce", "uploads", filename)
        saved_path = default_storage.save(upload_path, ContentFile(image.read()))
        image_url = f"{settings.MEDIA_URL}{saved_path}"

        return JsonResponse({"location": image_url})

    return JsonResponse({"error": "Invalid request"}, status=400)
