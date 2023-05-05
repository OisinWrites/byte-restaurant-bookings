from django.urls import path
from . import views

urlpatterns = [
     path('bookings/', views.bookings, name='bookings'),
     path('bookings/edit/<int:booking_id>/',
          views.edit_booking, name='edit_booking'),
     path('bookings/delete/<int:booking_id>/',
          views.delete_booking, name='delete_booking'),
     path('bookings/delete_table/<int:table_id>/',
          views.delete_table, name='delete_table'),
     path('bookings/manage/',
          views.bookings_management, name='bookings_management'),
]
