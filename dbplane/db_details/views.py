from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, "index.html", {})


'''def db_list(request, db_type):
    context = {
        'db_type': db_type,
        'title': f"{db_type.capitalize()} Connections",
    }
    return render(request, 'database_list.html', context) '''
def db_list(request, db_type):
    # Dummy data logic
    if db_type == 'mongo':
        dummy_connections = [
            {'name': 'Production_Cluster', 'id': 1},
            {'name': 'Staging_Logs', 'id': 2},
            {'name': 'User_Auth_DB', 'id': 3},
        ]
    elif db_type == 'postgres':
        dummy_connections = [
            {'name': 'Postgres_Main', 'id': 1},
            {'name': 'Inventory_DB', 'id': 2},
        ]
    else:
        dummy_connections = [
            {'name': f'Mock_{db_type}_Connection', 'id': 1},
        ]

    context = {
        'db_type': db_type,
        'connections': dummy_connections  # This is the variable your template loops over
    }
    return render(request, 'database_list.html', context)


def add_connection_form(request, db_type):
    # This view will serve the form page with the {% if %} logic we discussed
    return render(request, 'add_connection.html', {'db_type': db_type})