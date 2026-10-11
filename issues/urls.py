from django.urls import path
from .views import ReportersAPIView, IssuesAPIView

urlpatterns = [
    path("reporters/", ReportersAPIView.as_view(), name="reporters"),
    path("issues/", IssuesAPIView.as_view(), name="issues"),
]