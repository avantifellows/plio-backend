from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from django.shortcuts import render
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer


# Create your views here.
@csrf_exempt
def organization_list(request):
    """
    List all organizations, or create a new organization.
    """
    if request.method == "GET":
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == "POST":
        data = JSONParser().parse(request)
        serializer = OrganizationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def organization_detail(request, pk):
    """
    Retrieve, update or delete an organization.
    """
    try:
        organization = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = OrganizationSerializer(organization)
        return JsonResponse(serializer.data)

    elif request.method == "PUT":
        data = JSONParser().parse(request)
        serializer = OrganizationSerializer(organization, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    elif request.method == "DELETE":
        organization.delete()
        return HttpResponse(status=204)
