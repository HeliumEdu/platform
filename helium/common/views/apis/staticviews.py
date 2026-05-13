__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.views.generic import TemplateView


class RedocStaticView(TemplateView):
    template_name = 'redoc-static.html'


class HostAwareTemplateView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['scheme'] = self.request.scheme
        context['host'] = self.request.get_host()
        return context


class RobotsView(HostAwareTemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'


class SitemapView(HostAwareTemplateView):
    template_name = 'sitemap.xml'
    content_type = 'application/xml'
