from django.apps import AppConfig


# class DbdetailsConfig(AppConfig):
#     name = 'db_details'
#     def ready(self):
#         from .views import load_connections
#         load_connections()

class DbDetailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'db_details'