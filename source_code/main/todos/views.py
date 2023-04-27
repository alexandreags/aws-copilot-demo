from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from .models import Todo
import requests, uuid, os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()


# Create your views here.

def list_todo_items(request):
    todos = {'todo_list' : Todo.objects.all()[:10]}
    return render(request, 'todos/todo_list.html', todos)

def insert_todo_item(request:HttpRequest):
    todo = Todo(content = request.POST['content'])
    todo.save()
    # Send post to PUB Service
    #curl -X POST  <URL_ENDPOINT>/api/pub -d '{"text":"# Hello World"}' --header "Content-type: application/json"
    print('Todo Content in request: %s' % request.POST['content'] )
    #To reach the "api" service behind the internal load balancer
    endpoint = f"http://producer-sqs.%s.%s.internal/api/pub" % (os.environ.get("COPILOT_ENVIRONMENT_NAME"), os.environ.get("COPILOT_APPLICATION_NAME"))
    data = {
    "id": str(uuid.uuid4()),
    "text": str(request.POST['content'])
    }
    response = requests.post(endpoint, json=data)
    
    print('Todo Content json data %s' % data )
    
    print("Status Code", response.status_code)
    print("JSON Response ", response.json())
    
    return redirect('/todos/list')
    
def delete_todo_item(request,todo_id):
    todo_to_delete = Todo.objects.get(id=todo_id)
    todo_to_delete.delete()
    return redirect('/todos/list')