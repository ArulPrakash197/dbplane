"""
URL configuration for PasswordManager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from .views import (
    IndexView,
    AddConnectionView,
    DatabaseListView,
    DeleteConnectionView,
    EditConnectionView,
    TerminalPopupView,
    )

urlpatterns = [
    path("", IndexView.as_view(), name="home"),
    path("db/<str:db_type>/", DatabaseListView.as_view(), name="db_list"),
    path("db/<str:db_type>/add/", AddConnectionView.as_view(), name="add_connection_url"),
    path("db/<str:db_type>/delete/<int:index>/", DeleteConnectionView.as_view(), name="delete_connection"),
    path("db/<str:db_type>/edit/<int:index>/", EditConnectionView.as_view(), name="edit_connection"),
    path("db/<str:db_type>/terminal/", TerminalPopupView.as_view(), name="terminal_popup"),
]
