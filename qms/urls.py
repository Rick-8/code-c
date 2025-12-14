from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.create_interaction, name='qms_create'),
    path('manage/', views.qms_manager_list, name='qms_manager_list'),
    path('manage/<int:pk>/', views.qms_interaction_panel, name='qms_panel'),
    path('update/<int:pk>/', views.update_interaction, name='qms_update'),
]
