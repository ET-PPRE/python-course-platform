from .models import SiteData


def site_data(request):
    return {"site_data": SiteData.objects.first()}
