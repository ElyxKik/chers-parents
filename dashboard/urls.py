"""
URL configuration for dashboard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from app.views import home, ecoles, create_school, ecole_detail, update_school, create_professor, classes, create_classe, parents, create_parents, delete_parent,  eleves, create_eleve, professeurs, create_parents_api, create_professor_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('ecoles', ecoles, name='ecoles'),
    path('add_ecole',create_school, name='create_school' ),
    path('ecole/<str:school_id>', ecole_detail, name='ecole_detail'),
    path('edit_ecole/<str:school_id>', update_school, name='update_school'),
    path('create_professor/<str:ecole_id>', create_professor, name='create_professor'),
    path('professors/<str:ecole_id>', professeurs, name='professeurs'),
    path('parents/<str:ecole_id>', parents, name='parents'),
    path('create_parents/<str:ecole_id>', create_parents, name='create_parents'),
    path('delete_parent/<str:parent_id>/<str:school_id>', delete_parent, name='delete_parent'),
    path('classes/<str:ecole_id>', classes, name='classes'),
    path('create_classe/<str:ecole_id>', create_classe, name='create_classe'),
    path('eleves/<str:ecole_id>', eleves, name='eleves'),
    path('create_eleve/<str:ecole_id>', create_eleve, name='create_eleve'),
    path("create_parents_api/<str:ecole_id>", create_parents_api, name="create_parents_api"),
    path("create_professor_api/<str:ecole_id>", create_professor_api, name="create_professor_api"),

]
