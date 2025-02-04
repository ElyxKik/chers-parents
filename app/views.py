from django.shortcuts import render, redirect
from firebase_admin import auth, firestore
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm, CustomAuthenticationForm
from django.contrib import messages 
from django.http import JsonResponse
import json
import random
import string


# Create your views here.

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Connecte automatiquement l'utilisateur après l'inscription
            return redirect('home')  # Remplacez 'home' par la vue souhaitée
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Remplacez 'home' par la vue après connexion
    else:
        form = CustomAuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')  # Redirigez l'utilisateur après la déconnexion


def generate_password(length=8):
    """Génère un mot de passe aléatoire."""
    if length < 8:
        raise ValueError("La longueur du mot de passe doit être d'au moins 8 caractères.")
    
    # Définir les caractères possibles
    characters = string.ascii_letters + string.digits 
    
    # Générer un mot de passe aléatoire
    password = ''.join(random.choice(characters) for _ in range(length))
    return password


def home(request):
    # Initialiser Firestore
    db = firestore.client()
    
    try:
        # Récupérer le nombre de documents dans chaque collection
        nombre_ecole = len(list(db.collection('ecole').stream()))
        nombre_professor = len(list(db.collection('professor').stream()))
        nombre_classe = len(list(db.collection('classe').stream()))
        nombre_eleve = len(list(db.collection('student').stream()))
        
        # Passer les données au template
        return render(request, 'home.html', {
            'nombre_ecole': nombre_ecole,
            'nombre_professor': nombre_professor,
            'nombre_classe': nombre_classe,
            'nombre_eleve': nombre_eleve,
        })
    except Exception as e:
        # En cas d'erreur, afficher un message dans le template
        return render(request, 'home.html', {'error': str(e)})



def ecoles(request):
    try:
        # Connexion à Firestore
        db = firestore.client()

        # Récupérer toutes les écoles dans la collection "ecole"
        schools_ref = db.collection("ecole")
        schools = [
        {**doc.to_dict(), "id": doc.id}  # Combiner les données avec l'identifiant
        for doc in schools_ref.stream()
    ]

        return render(request, 'ecoles.html', {'schools':schools})
    except Exception as e:
        return render(request, "ecoles.html", {"error": f"Erreur : {str(e)}"})



def ecole_detail(request, school_id):
    db = firestore.client()
    school_ref = db.collection("ecole").document(school_id)

    try:
        # Récupérer les données du document de l'école
        school = school_ref.get()
        if school.exists:
            school_data = school.to_dict()
            school_data["id"] = school.id  # Inclure l'ID du document dans les données

            # Initialiser la variable pour vérifier si l'école est activée
            ecole_activated = False

            # Récupérer l'utilisateur associé à l'école
            user_ref = school_data.get("user")  # Peut être un DocumentReference
            if isinstance(user_ref, firestore.DocumentReference):
                user_id = user_ref.id  # Extraire l'ID du DocumentReference
                user_doc = db.collection("users").document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    ecole_activated = user_data.get("ecole_activated", False)

            # Ajouter la variable ecole_activated aux données à transmettre au template
            school_data["ecole_activated"] = ecole_activated

            return render(request, 'ecole_detail.html', {"school": school_data})
        else:
            # Gérer le cas où le document de l'école n'existe pas
            return render(request, "404.html", {"error": "École introuvable"})
    except Exception as e:
        messages.error(request, f"Une erreur s'est produite : {str(e)}")
        return redirect("ecoles")



def create_school(request):
    if request.method == "POST":

        # Récupération des données utilisateur et école
        nom_ecole = request.POST.get("nom")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        adresse = request.POST.get("adresse")
        responsable = request.POST.get("responsable")

        password= generate_password(8)

        try:
            # Créer l'utilisateur Firebase
            user = auth.create_user(
                email=email,
                password= password  # Un mot de passe par défaut
            )

            # Initialiser Firestore
            db = firestore.client()

            created_time  = firestore.SERVER_TIMESTAMP

            # Ajouter les informations école dans la collection "ecole"
            school_data = {
                "nom": nom_ecole,
                "adresse": adresse,
                "responsable": responsable,
                "created_time": created_time,
                "user_id": user.uid,
            }
            # Ajouter le document et récupérer la référence
            school_ref = db.collection("ecole").add(school_data)
            school_id = school_ref[1].id  # Récupérer l'ID du document créé

            # Ajouter les informations utilisateur dans la collection "users"
            user_data = {
                "email": email,
                "display_name": nom_ecole,
                "phone_number": phone,
                "user_id": user.uid,
                "compte_id": school_id,  # Utiliser l'ID de l'école ici
                "is_school": True,
                "created_time": created_time,
            }
            db.collection("users").document(user.uid).set(user_data)

            # Ajouter un message de succès
            messages.success(request, f"L'utilisateur et l'école '{nom_ecole}' ont été créés avec succès. mot de passe {password}")

            # Rediriger l'utilisateur vers la page Django 'ecole'
            return redirect("ecoles")  # Assurez-vous que la route 'ecole' est définie.

        except Exception as e:
            # Ajouter un message d'erreur
            messages.error(request, f"Une erreur s'est produite : {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)



def update_school(request, school_id):
    db = firestore.client()
    school_ref = db.collection("ecole").document(school_id)

    if request.method == "POST":
        # Récupérer les données du formulaire
        nom = request.POST.get("nom")
        adresse = request.POST.get("adresse")
        responsable = request.POST.get("responsable")

        try:
            # Mettre à jour le document
            school_ref.update({
                "nom": nom,
                "adresse": adresse,
                "responsable": responsable,
            })
            # Rediriger avec un message de succès
            return redirect("ecole_detail", school_id=school_id)
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            return redirect("ecole_detail", school_id)

    # Pré-remplir les champs avec les données existantes
    school = school_ref.get()
    if school.exists:
        school_data = school.to_dict()
        school_data["id"] = school.id
        return render(request, "ecole_detail.html", {"school": school_data})
    else:
        messages.error(request, f"École introuvable: {str(e)}")
        return redirect("ecole_detail", school_id)
    

def delete_school(request, school_id):
    db = firestore.client()
    school_ref = db.collection("ecole").document(school_id)

    try:
        # Vérifier si le document existe
        school = school_ref.get()
        if not school.exists:
            messages.error(request, "L'école spécifiée n'existe pas.")
            return redirect("ecoles")  # Rediriger vers la liste des écoles ou une autre page

        # Supprimer le document
        school_ref.delete()

        messages.success(request, "L'école a été supprimée avec succès.")
        return redirect("ecoles")  # Rediriger vers la liste des écoles après suppression

    except Exception as e:
        messages.error(request, f"Une erreur s'est produite : {str(e)}")
        return redirect("ecoles")  # Rediriger vers une page appropriée en cas d'erreur


def create_professor(request, ecole_id):
    if request.method == "POST":
        # Récupérer les données du formulaire
        nom_professeur = request.POST.get("nom")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        sexe = request.POST.get("sexe")
        classe = request.POST.get("classe")
        adresse = request.POST.get("adresse")

        # Générer un mot de passe aléatoire
        password = generate_password(8)

        try:
            # Créer l'utilisateur Firebase
            user = auth.create_user(
                email=email,
                password=password
            )

            # Initialiser Firestore
            db = firestore.client()
            created_time = firestore.SERVER_TIMESTAMP


            # Ajouter les informations du professeur dans la collection "professor"
            professor_data = {
                "nom": nom_professeur,
                "telephone": phone,
                "email": email,
                "adresse": adresse,
                "classe": classe,
                "sexe": sexe,
                "created_time": created_time,
                "user_id": user.uid,
                "ecole": ecole_id,
            }
            # Ajouter le document et récupérer la référence
            professor_ref = db.collection("professor").add(professor_data)
            professor_id = professor_ref[1].id  # Récupérer l'ID du document créé

            # Ajouter les informations utilisateur dans la collection "users"
            user_data = {
                "email": email,
                "display_name": nom_professeur,
                "phone_number": phone,
                "user_id": user.uid,
                "compte_id": professor_id,  # Utiliser l'ID du professeur ici
                "is_professor": True,
                "created_time": created_time,
            }

            db.collection("users").document(user.uid).set(user_data)

            # Ajouter un message de succès
            messages.success(
                request,
                f"L'utilisateur '{nom_professeur}' a été créé avec succès. Mot de passe : {password}"
            )

            # Rediriger l'utilisateur vers la page des professeurs
            return redirect("professeurs", ecole_id)  # Assurez-vous que cette route existe.

        except Exception as e:
            # Ajouter un message d'erreur
            messages.error(request, f"Une erreur s'est produite : {str(e)}")
            return redirect("professeurs", ecole_id)

    # Si ce n'est pas une requête POST
    return render(request, "professors.html")



def activate_school(request, ecole_id):
    try:
        db = firestore.client()

        # Récupérer le document de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()

        # Vérifier si l'école existe
        if not school_doc.exists:
            messages.error(request, "L'école spécifiée n'existe pas.")
            return redirect("ecoles")  # Redirige vers la liste des écoles ou une autre page appropriée

        # Récupérer le champ "user" du document de l'école
        school_data = school_doc.to_dict()
        user_ref = school_data.get("user")

        # Vérifier si le champ "user" existe
        if not user_ref:
            messages.error(request, "Le champ 'user' est manquant dans le document de l'école.")
            return redirect("ecole_detail", ecole_id)

        # Extraire l'ID de l'utilisateur
        if isinstance(user_ref, firestore.DocumentReference):
            user_id = user_ref.id  # Si c'est un DocumentReference, extraire l'ID
        else:
            user_id = user_ref  # Si ce n'est pas un DocumentReference, utiliser directement

        # Récupérer le document de l'utilisateur
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        # Vérifier si l'utilisateur existe
        if not user_doc.exists:
            messages.error(request, "L'utilisateur spécifié n'existe pas.")
            return redirect("ecole_detail", ecole_id)

        # Mettre à jour le champ "ecole_activated"
        user_ref.update({"ecole_activated": True})

        messages.success(request, "L'école et l'utilisateur associés ont été activés avec succès.")
        return redirect("ecole_detail", ecole_id)  # Redirige vers la page de détails de l'école

    except Exception as e:
        # Gestion globale des exceptions
        messages.error(request, f"Une erreur s'est produite : {str(e)}")
        return redirect("ecole_detail", ecole_id)




def professeurs(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return render(request, "parents.html", {"error": "L'école spécifiée n'existe pas."})

        school = school_doc.to_dict()

        # Filtrer les professeurs associés à l'école
        parents_ref = db.collection("professor").where("ecole", "==", ecole_id)
        parents = [parent.to_dict() for parent in parents_ref.stream()]

        # Filtrer les classes associés à l'école
        classe_ref = db.collection("classe").where("ecole", "==", ecole_id)
        classe = [classe.to_dict() for classe in classe_ref.stream()]

        # Rendre le template avec les données
        return render(request, "professors.html", {
            "parents": parents,
            "school": school,
            "ecole_id": ecole_id,
            "classe": classe
        })
    
    except Exception as e:
        return render(request, "professors.html", {"error": str(e)})


def parents(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return render(request, "parents.html", {"error": "L'école spécifiée n'existe pas."})

        school = school_doc.to_dict()

        # Filtrer les professeurs associés à l'école
        parents_ref = db.collection("parents").where("ecole", "==", ecole_id)
        parents = [parent.to_dict() for parent in parents_ref.stream()]

        # Rendre le template avec les données
        return render(request, "parents.html", {
            "parents": parents,
            "school": school,
            "ecole_id": ecole_id,
        })
    
    except Exception as e:
        return render(request, "parents.html", {"error": str(e)})


def create_parents(request, ecole_id):
    if request.method == "POST":
        # Récupérer les données du formulaire
        nom_pere = request.POST.get("nom_pere")
        nom_mere = request.POST.get("nom_mere")
        phone_pere = request.POST.get("phone_pere")
        phone_mere = request.POST.get("phone_mere")
        email = request.POST.get("email")
        adresse = request.POST.get("adresse")
        nationalite = request.POST.get("nationalite")
        nom_gardien = request.POST.get("nom_gardien")
        phone_tuteur = request.POST.get("phone_tuteur")
        province = request.POST.get("province")

        # Générer un mot de passe aléatoire
        password = generate_password(8)

        try:
            # Créer l'utilisateur Firebase
            user = auth.create_user(
                email=email,
                password=password
            )

            # Initialiser Firestore
            db = firestore.client()
            created_time = firestore.SERVER_TIMESTAMP

            # Ajouter les informations du professeur dans la collection "professor"
            parents_data = {
                "nom_pere": nom_pere,
                "nom_mere": nom_mere,
                "telephone_pere": phone_pere,
                "telephone_mere": phone_mere,
                "email": email,
                "adresse": adresse,
                "nationalite": nationalite,
                "nom_gardien": nom_gardien,
                "phone_tuteur": phone_tuteur,
                "province": province,
                "created_time": created_time,
                "user_id": user.uid,
                "ecole": ecole_id
            }
            # Ajouter le document dans la collection "parents" et récupérer l'ID
            parent_ref = db.collection("parents").add(parents_data)
            parent_id = parent_ref[1].id  # Récupérer l'ID du document créé

            # Ajouter les informations utilisateur dans la collection "users"
            user_data = {
                "email": email,
                "display_name": nom_pere,
                "phone_number": phone_pere,
                "user_id": user.uid,
                "compte_id": parent_id,  # Utiliser l'ID des parents ici
                "is_professor": True,
                "created_time": created_time,
            }
            db.collection("users").document(user.uid).set(user_data)

            # Ajouter un message de succès
            messages.success(
                request,
                f"Les des parents '{nom_pere}' et '{nom_mere}' a été créé avec succès. Mot de passe : {password}"
            )

            # Rediriger l'utilisateur vers la page des professeurs
            return redirect("parents", ecole_id)  # Assurez-vous que cette route existe.

        except Exception as e:
            # Ajouter un message d'erreur
            messages.error(request, f"Une erreur s'est produite : {str(e)}")
            return redirect("parents", ecole_id)

    # Si ce n'est pas une requête POST
    return render(request, "parents.html")



def update_parent(request, ecole_id, parent_id):
    db = firestore.client()
    parents = db.collection("parents").document(parent_id)

    if request.method == "POST":
        # Récupérer les données du formulaire
        nom_pere = request.POST.get("nom_pere")
        nom_mere = request.POST.get("nom_mere")
        phone_pere = request.POST.get("phone_pere")
        phone_mere = request.POST.get("phone_mere")
        adresse = request.POST.get("adresse")
        nationalite = request.POST.get("nationalite")
        nom_gardien = request.POST.get("nom_gardien")
        phone_tuteur = request.POST.get("phone_tuteur")
        province = request.POST.get("province")

        try:
            # Mettre à jour le document
            parents.update({
                "nom_pere": nom_pere,
                "nom_mere": nom_mere,
                "telephone_pere": phone_pere,
                "telephone_mere": phone_mere,   
                "adresse": adresse,
                "nationalite": nationalite,
                "nom_gardien": nom_gardien,
                "phone_tuteur": phone_tuteur,
                "province": province,
            })
            # Rediriger avec un message de succès
            return redirect("parents", ecole_id=ecole_id)
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            return redirect("parents", ecole_id)

    
    messages.error(request, f"Parents introuvable: {str(e)}")
    return redirect("parents", ecole_id)



def delete_parent(request, ecole_id, parent_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Référence au document à supprimer
        parent_ref = db.collection("parents").document(parent_id)
        
        # Supprimer le document
        parent_ref.delete()

        # Ajouter un message de succès
        messages.success(request, "Le parent a été supprimé avec succès.")
    except Exception as e:
        # Ajouter un message d'erreur
        messages.error(request, f"Une erreur s'est produite lors de la suppression : {e}")

    # Rediriger vers la page des parents
    return redirect("parents", ecole_id=ecole_id)


def classes(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return render(request, "classes.html", {"error": "L'école spécifiée n'existe pas."})

        school = school_doc.to_dict()

        # Filtrer les classes associés à l'école
        classe_ref = db.collection("classe").where("ecole", "==", ecole_id)
        classe = [classe.to_dict() for classe in classe_ref.stream()]

        # Rendre le template avec les données
        return render(request, "classes.html", {
            "classe": classe,
            "school": school,
            "ecole_id": ecole_id
        })
    
    except Exception as e:
        return render(request, "classes.html", {"error": str(e)})


def create_classe(request, ecole_id):
    if request.method == "POST":
        # Récupérer les données du formulaire
        nom= request.POST.get("nom")

        try:    
            db = firestore.client()

            class_data = {
                "nom": nom,
                "ecole": ecole_id,
                "nombre_eleve": 0
            }
            db.collection("classe").add(class_data)

            messages.success(
                    request,
                    f"La classe '{nom}' a été créé avec succès!")
            return redirect("classes", ecole_id)
        
        except Exception as e:
            # Ajouter un message d'erreur
            messages.error(request, f"Une erreur s'est produite : {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)



def eleves(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return render(request, "eleves.html", {"error": "L'eleve spécifiée n'existe pas."})

        school = school_doc.to_dict()

        # Filtrer les professeurs associés à l'école
        eleves_ref = db.collection("student").where("ecole", "==", ecole_id)
        eleves = [eleve.to_dict() for eleve in eleves_ref.stream()]

        classe_ref = db.collection("classe").where("ecole", "==", ecole_id)
        classes = [classe.to_dict() for classe in classe_ref.stream()]

        parents_ref = db.collection("parents").where("ecole", "==", ecole_id)
        parents = [parent.to_dict() for parent in parents_ref.stream()]

        # Rendre le template avec les données
        return render(request, "eleves.html", {
            "eleves":  eleves,
            "school": school,
            "ecole_id": ecole_id,
            "parents": parents,
            "classes": classes,
        })
    
    except Exception as e:
        return render(request, "eleves.html", {"error": str(e)})


def create_eleve(request, ecole_id):
    if request.method == "POST":
        # Récupérer les données du formulaire
        nom = request.POST.get("nom")
        post_nom = request.POST.get("post_nom")
        prenom = request.POST.get("prenom")
        sexe = request.POST.get("sexe")
        date_naissance = request.POST.get("date_naissance")
        adresse = request.POST.get("adresse")
        email = request.POST.get("email")
        telephone = request.POST.get("telephone")
        classe = request.POST.get("classe")
        parents = request.POST.get("parents")

        try:
            # Initialiser Firestore
            db = firestore.client()
            created_time = firestore.SERVER_TIMESTAMP

            # Ajouter les informations du professeur dans la collection "professor"
            eleves_data = {
                "nom": nom,
                "post_nom": post_nom,
                "prenom": prenom,
                "sexe": sexe,
                "date_naissance": date_naissance,
                "adresse": adresse,
                "email": email,
                "telephone": telephone,
                "classe": classe,
                "ecole" : ecole_id,
                "parents": parents,
                "created_time": created_time,
            }
            db.collection("student").add(eleves_data)

            # Ajouter un message de succès
            messages.success(
                request,
                f"L'eleve '{nom}' '{post_nom}' '{prenom}' a été créé avec succès!"
            )

            # Rediriger l'utilisateur vers la page des professeurs
            return redirect("eleves", ecole_id)  # Assurez-vous que cette route existe.

        except Exception as e:
            # Ajouter un message d'erreur
            messages.error(request, f"Une erreur s'est produite : {str(e)}")
            return redirect("eleves", ecole_id)

    # Si ce n'est pas une requête POST
    return render(request, "eleves.html")

#API ENDPOINT

@csrf_exempt
def create_parents_api(request, ecole_id):
    if request.method == "POST":
        try:
            # Charger les données JSON de la requête
            data = json.loads(request.body)

            # Récupérer les données du parent
            nom_pere = data.get("nom_pere")
            nom_mere = data.get("nom_mere")
            phone_pere = data.get("phone_pere")
            phone_mere = data.get("phone_mere")
            email = data.get("email")
            adresse = data.get("adresse")
            nationalite = data.get("nationalite")
            nom_gardien = data.get("nom_gardien")
            phone_tuteur = data.get("phone_tuteur")
            province = data.get("province")

            # Générer un mot de passe aléatoire
            password = generate_password(8)

            # Créer l'utilisateur Firebase
            user = auth.create_user(email=email, password=password)

            # Initialiser Firestore
            db = firestore.client()
            created_time = firestore.SERVER_TIMESTAMP

            # Ajouter les informations du parent dans la collection "parents"
            parents_data = {
                "nom_pere": nom_pere,
                "nom_mere": nom_mere,
                "telephone_pere": phone_pere,
                "telephone_mere": phone_mere,
                "email": email,
                "adresse": adresse,
                "nationalite": nationalite,
                "nom_gardien": nom_gardien,
                "phone_tuteur": phone_tuteur,
                "province": province,
                "created_time": created_time,
                "user_id": user.uid,
                "ecole": ecole_id,
            }
            parent_ref = db.collection("parents").add(parents_data)
            parent_id = parent_ref[1].id  # Récupérer l'ID du document créé

            # Ajouter les informations utilisateur dans la collection "users"
            user_data = {
                "email": email,
                "display_name": nom_pere,
                "phone_number": phone_pere,
                "user_id": user.uid,
                "compte_id": parent_id,  # Utiliser l'ID des parents ici
                "is_parents": True,  # Modifier si ce champ est mal nommé
                "parents_ref": parent_ref,
                "created_time": created_time,
            }
            db.collection("users").document(user.uid).set(user_data)

            # Réponse succès
            return JsonResponse({
                "message": f"Les parents '{nom_pere}' et '{nom_mere}' ont été créés avec succès.",
                "parent_id": parent_id,
                "user_id": user.uid,
                "password": password,
            }, status=201)

        except Exception as e:
            # Réponse d'erreur
            return JsonResponse({"error": str(e)}, status=500)

    # Réponse si la méthode n'est pas POST
    return JsonResponse({"error": "Méthode non autorisée."}, status=405)



@csrf_exempt
def create_professor_api(request, ecole_id):
    if request.method == "POST":
        try:
            # Charger les données JSON de la requête
            data = json.loads(request.body)

            # Récupérer les données du professeur
            nom_professeur = data.get("nom")
            email = data.get("email")
            phone = data.get("phone")
            sexe = data.get("sexe")
            classe = data.get("classe")
            adresse = data.get("adresse")

            # Générer un mot de passe aléatoire
            password = generate_password(8)

            # Créer l'utilisateur Firebase
            user = auth.create_user(email=email, password=password)

            # Initialiser Firestore
            db = firestore.client()
            created_time = firestore.SERVER_TIMESTAMP

            # Ajouter les informations du professeur dans la collection "professor"
            professor_data = {
                "nom": nom_professeur,
                "telephone": phone,
                "email": email,
                "adresse": adresse,
                "classe": classe,
                "sexe": sexe,
                "created_time": created_time,
                "user_id": user.uid,
                "ecole": ecole_id,
            }
            # Ajouter le document et récupérer l'ID
            professor_ref = db.collection("professor").add(professor_data)
            professor_id = professor_ref[1].id  # Récupérer l'ID du document créé

            # Ajouter les informations utilisateur dans la collection "users"
            user_data = {
                "email": email,
                "display_name": nom_professeur,
                "phone_number": phone,
                "user_id": user.uid,
                "compte_id": professor_id,  # Utiliser l'ID du professeur ici
                "is_professor": True,
                "prof_ref": professor_ref,
                "created_time": created_time,
            }
            db.collection("users").document(user.uid).set(user_data)

            # Réponse succès
            return JsonResponse({
                "message": f"L'utilisateur '{nom_professeur}' a été créé avec succès.",
                "professor_id": professor_id,
                "user_id": user.uid,
                "password": password,
            }, status=201)

        except Exception as e:
            # Réponse d'erreur
            return JsonResponse({"error": str(e)}, status=500)

    # Réponse si la méthode n'est pas POST
    return JsonResponse({"error": "Méthode non autorisée."}, status=405)


def get_professors_api(request, ecole_id):
    if request.method == "GET":
        try:
            # Initialiser Firestore
            db = firestore.client()

            # Récupérer les détails de l'école
            school_ref = db.collection("ecole").document(ecole_id)
            school_doc = school_ref.get()

            if not school_doc.exists:
                return JsonResponse({"error": "L'école spécifiée n'existe pas."}, status=404)

            school = school_doc.to_dict()

            # Filtrer les professeurs associés à l'école
            professor_ref = db.collection("professor").where("ecole", "==", ecole_id)
            professors = [professor.to_dict() for professor in professor_ref.stream()]

            # Filtrer les classes associées à l'école
            classe_ref = db.collection("classe").where("ecole", "==", ecole_id)
            classes = [classe.to_dict() for classe in classe_ref.stream()]

            # Retourner les données en JSON
            return JsonResponse({
                "school": school,
                "professors": professors,
                "classes": classes,
                "ecole_id": ecole_id
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # Retourner une erreur pour toute autre méthode HTTP
    return JsonResponse({"error": "Méthode non autorisée."}, status=405)


def get_parents_api(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return JsonResponse({"error": "L'école spécifiée n'existe pas."}, status=404)

        school = school_doc.to_dict()

        # Filtrer les parents associés à l'école
        parents_ref = db.collection("parents").where("ecole", "==", ecole_id)
        parents = [parent.to_dict() for parent in parents_ref.stream()]

        # Retourner les données en JSON
        return JsonResponse({
            "school": school,
            "parents": parents,
            "ecole_id": ecole_id,
        }, status=200)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def get_eleves_api(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return JsonResponse({"error": "L'école spécifiée n'existe pas."}, status=404)

        school = school_doc.to_dict()

        # Filtrer les élèves associés à l'école
        eleves_ref = db.collection("student").where("ecole", "==", ecole_id)
        eleves = [eleve.to_dict() for eleve in eleves_ref.stream()]

        # Filtrer les classes associées à l'école
        classe_ref = db.collection("classe").where("ecole", "==", ecole_id)
        classes = [classe.to_dict() for classe in classe_ref.stream()]

        # Filtrer les parents associés à l'école
        parents_ref = db.collection("parents").where("ecole", "==", ecole_id)
        parents = [parent.to_dict() for parent in parents_ref.stream()]

        # Retourner les données en JSON
        return JsonResponse({
            "school": school,
            "eleves": eleves,
            "ecole_id": ecole_id,
            "parents": parents,
            "classes": classes,
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


def get_classes_api(request, ecole_id):
    # Initialiser Firestore
    db = firestore.client()

    try:
        # Récupérer les détails de l'école
        school_ref = db.collection("ecole").document(ecole_id)
        school_doc = school_ref.get()
        
        if not school_doc.exists:
            return JsonResponse({"error": "L'école spécifiée n'existe pas."}, status=404)

        school = school_doc.to_dict()

        # Filtrer les classes associées à l'école
        classe_ref = db.collection("classe").where("ecole", "==", ecole_id)
        classes = [classe.to_dict() for classe in classe_ref.stream()]

        # Retourner les données en JSON
        return JsonResponse({
            "school": school,
            "classes": classes,
            "ecole_id": ecole_id
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

def create_classe_api(request, ecole_id):
    if request.method == "POST":
        try:
            # Initialiser Firestore
            db = firestore.client()

            # Récupérer les données du corps de la requête
            data = json.loads(request.body)
            nom = data.get("nom")

            if not nom:
                return JsonResponse({"error": "Le nom de la classe est requis."}, status=400)

            # Vérifier si l'école existe
            school_ref = db.collection("ecole").document(ecole_id)
            if not school_ref.get().exists:
                return JsonResponse({"error": "L'école spécifiée n'existe pas."}, status=404)

            # Créer les données pour la classe
            class_data = {
                "nom": nom,
                "ecole": ecole_id,
                "nombre_eleve": 0
            }

            # Ajouter la classe dans Firestore
            db.collection("classe").add(class_data)

            return JsonResponse({"message": f"La classe '{nom}' a été créée avec succès."}, status=201)

        except Exception as e:
            return JsonResponse({"error": f"Une erreur s'est produite : {str(e)}"}, status=500)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)
    

def create_eleve_api(request, ecole_id):
    if request.method == "POST":
        try:
            # Initialiser Firestore
            db = firestore.client()

            # Vérifier si l'école existe
            school_ref = db.collection("ecole").document(ecole_id)
            school_doc = school_ref.get()
            if not school_doc.exists:
                return JsonResponse({"error": "L'école spécifiée n'existe pas."}, status=404)

            # Récupérer les données du corps de la requête
            data = json.loads(request.body)
            nom = data.get("nom")
            prenom = data.get("prenom")
            date_naissance = data.get("date_naissance")
            classe_id = data.get("classe_id")
            parent_id = data.get("parent_id")

            if not nom or not prenom or not date_naissance or not classe_id or not parent_id:
                return JsonResponse({"error": "Tous les champs sont requis."}, status=400)

            # Vérifier si la classe existe
            classe_ref = db.collection("classe").document(classe_id)
            if not classe_ref.get().exists:
                return JsonResponse({"error": "La classe spécifiée n'existe pas."}, status=404)

            # Vérifier si le parent existe
            parent_ref = db.collection("parents").document(parent_id)
            if not parent_ref.get().exists:
                return JsonResponse({"error": "Le parent spécifié n'existe pas."}, status=404)

            # Générer un identifiant aléatoire pour l'élève
            eleve_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

            # Ajouter les informations de l'élève dans Firestore
            eleve_data = {
                "nom": nom,
                "prenom": prenom,
                "date_naissance": date_naissance,
                "classe_id": classe_id,
                "parent_id": parent_id,
                "ecole": ecole_id,
                "eleve_id": eleve_id
            }
            db.collection("student").document(eleve_id).set(eleve_data)

            return JsonResponse({"message": "Élève créé avec succès.", "eleve": eleve_data}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Méthode non autorisée."}, status=405)