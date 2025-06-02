from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),        # includes the root redirect
    path('dashboard/', include('dashboard.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),        # for login/logout/etc
    path('dashboard/', include('dashboard.urls')),  # dashboard stuff
    path('', include('dashboard.urls')),       # required for /submit-lead/
]