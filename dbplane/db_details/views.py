from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, "index.html", {})


def mongoCon(request):
    return render(request, template_name="mongoCon.html", context={})


def redisCon(request):
    return render(request, template_name="redisCon.html", context={})


def postgresqlCon(request):
    return render(request, template_name="postgresqlCon.html", context={})


def rabbitmqCon(request):
    return render(request, template_name="rabbitmqCon.html", context={})