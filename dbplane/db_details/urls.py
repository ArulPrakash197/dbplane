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
from django.views.generic import TemplateView
from .views import (
    IndexView,
    ClusterConfigurationView,
    AddConnectionView,
    DatabaseListView,
    DeleteConnectionView,
    EditConnectionView,
    ConnectionSecretView,
    TerminalPopupView,
    TerminalExecuteView,
    TerminalAutocompleteView,
    TerminalConnectView,
    TestConnectionApiView,
    ClusterListView,
    AddClusterView,
    EditClusterView,
    DeleteClusterView,
    ClusterVerifyApiView,
    DeployClusterView,
    ClusterDeployApiView,
    ClusterDeployStreamView,
    DeploymentResultsApiView,
    DeploymentLiveStreamView,
    )


urlpatterns = [
    path("", IndexView.as_view(), name="home"),
    path("cluster-configuration/", ClusterConfigurationView.as_view(), name="cluster_configuration"),
    path("cluster-configuration/db/<str:db_type>/", ClusterListView.as_view(), name="cluster_list"),
    path("cluster-configuration/db/<str:db_type>/add/", AddClusterView.as_view(), name="add_cluster"),
    path("cluster-configuration/db/<str:db_type>/edit/<int:index>/", EditClusterView.as_view(), name="edit_cluster"),
    path("cluster-configuration/db/<str:db_type>/delete/<int:index>/", DeleteClusterView.as_view(), name="delete_cluster"),
    path("cluster-configuration/db/<str:db_type>/deploy/<int:index>/", DeployClusterView.as_view(), name="deploy_cluster"),
    path("cluster-configuration/db/<str:db_type>/deploy-api/<int:index>/", ClusterDeployApiView.as_view(), name="cluster_deploy_api"),
    path("cluster-configuration/db/<str:db_type>/deploy-stream/<int:index>/", ClusterDeployStreamView.as_view(), name="cluster_deploy_stream"),
    path("cluster-configuration/db/<str:db_type>/results-api/<int:index>/", DeploymentResultsApiView.as_view(), name="deployment_results_api"),
    path("cluster-configuration/db/<str:db_type>/results-api/<int:index>/job/<int:job_id>/live/", DeploymentLiveStreamView.as_view(), name="deployment_live_stream"),
    path("cluster-configuration/db/<str:db_type>/verify-api/", ClusterVerifyApiView.as_view(), name="cluster_verify_api"),
    path("dashboard/", TemplateView.as_view(template_name="dashboard.html"), name="dashboard"),
    path("db/<str:db_type>/", DatabaseListView.as_view(), name="db_list"),
    path("db/<str:db_type>/add/", AddConnectionView.as_view(), name="add_connection_url"),
    path("db/<str:db_type>/delete/<int:index>/", DeleteConnectionView.as_view(), name="delete_connection"),
    path("db/<str:db_type>/edit/<int:index>/", EditConnectionView.as_view(), name="edit_connection"),
    path("db/<str:db_type>/secret/<int:index>/", ConnectionSecretView.as_view(), name="connection_secret"),
    path("db/<str:db_type>/test-api/", TestConnectionApiView.as_view(), name="test_connection_api"),
    path("db/<str:db_type>/terminal/", TerminalPopupView.as_view(), name="terminal_popup"),
    path("db/terminal/execute/", TerminalExecuteView.as_view(), name="terminal_execute"),
    path("db/terminal/autocomplete/", TerminalAutocompleteView.as_view(), name="terminal_autocomplete"),
    path("db/terminal/connect/", TerminalConnectView.as_view(), name="terminal_connect"),
]
