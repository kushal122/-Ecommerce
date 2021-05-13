from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('eco.urls', namespace='eco')),
    path('api/v1/', include('social_django.urls', namespace='social')),
]
if settings.DEBUG:
    if settings.DEBUG:
        import debug_toolbar

        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
        urlpatterns += static(settings.MEDIA_URL,
                              document_root=settings.MEDIA_ROOT)
        urlpatterns += static(settings.STATIC_URL,
                              document_root=settings.STATIC_ROOT)
