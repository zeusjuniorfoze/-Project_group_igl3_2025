# Base de données

Copiez `.env.example` vers `.env` et remplacez les clés secrètes par des valeurs
aléatoires distinctes avant de lancer l'application. Ne partagez pas et ne
commitez jamais le fichier `.env`. En production, configurez `APP_ENV=production`
et activez HTTPS; l'application refuse alors de démarrer sans `SECRET_KEY` et
`JWT_SECRET_KEY`, et impose le cookie de session `Secure`.

Depuis le dossier `birth_certification_system`, appliquer les migrations avec :

```powershell
python -m flask --app run.py db upgrade
```

Après une modification des modèles dans `app/models.py`, créer puis appliquer une migration :

```powershell
python -m flask --app run.py db migrate -m "Description de la modification"
python -m flask --app run.py db upgrade
```

Pour vérifier la révision appliquée ou détecter un écart entre les modèles et la base :

```powershell
python -m flask --app run.py db current
python -m flask --app run.py db check
```

## Génération des actes PDF

La génération des actes requiert également l'exécutable `wkhtmltopdf` (le paquet
Python `pdfkit` ne l'inclut pas). Sous Windows, installez wkhtmltopdf, puis
ajoutez son dossier `bin` au `PATH`. Si le binaire n'est pas dans le `PATH`,
définissez `WKHTMLTOPDF_PATH` dans `.env`, par exemple :

```dotenv
WKHTMLTOPDF_PATH=C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe
```

## Créer le compte administrateur initial

Depuis `birth_certification_system`, lancez :

```powershell
python -m flask --app run.py admin create-admin
```

La commande crée le compte `Fozet Junior` (`fozetj29@fmail.com`) et demande le
mot de passe sans l'afficher (12 caractères minimum). Les variables
`ADMIN_PASSWORD`, `ADMIN_USERNAME` et `ADMIN_EMAIL` permettent de fournir les
valeurs depuis l'environnement. La commande refuse de modifier un compte existant.

## Authentification et sécurité

Les routes d'administration, d'hôpital et de mairie vérifient le compte et son
rôle depuis la base à chaque requête. Les formulaires POST utilisent une
protection CSRF; la déconnexion se fait par POST. Les demandes de réinitialisation
ne révèlent pas si une adresse est enregistrée; les codes expirent après 30 minutes,
sont hachés et limités à cinq essais, avec un délai entre deux demandes.