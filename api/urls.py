from django.urls import path
from . import views

urlpatterns = [
    path('purchase_naive_wrong', views.NaivePurchaseView.as_view(), name='purchase'),
    path('purchase_transactional/', views.TransactionalPurchaseView.as_view(),name='transaction'),
    path('purchase_high_speed/', views.HighSpeedPurchaseView.as_view(), name='high_speed_purchase'),
]