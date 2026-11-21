# Air Quality DataOps/MLOps

Plateforme universitaire de surveillance de la qualité de l'air. Le dépôt est au démarrage : cette première configuration lance PostgreSQL en local et prépare l'environnement Python. Kafka, Spark, Airflow, MLflow, l'API et le dashboard seront ajoutés dans les phases suivantes.

## Prérequis

- Git
- Python 3.11 ou plus récent
- Docker Desktop avec Docker Compose v2

Vérifier les installations :

```powershell
python --version
docker --version
docker compose version
```

## Démarrage rapide (Windows PowerShell)

Depuis la racine du dépôt :

1. Créer le fichier local de configuration à partir du modèle :

   ```powershell
   Copy-Item .env.example .env
   ```

2. Démarrer PostgreSQL :

   ```powershell
   docker compose --env-file .env -f infra/docker-compose.yml up -d
   docker compose --env-file .env -f infra/docker-compose.yml ps
   ```

3. Créer et activer l'environnement Python :

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Vérifier que PostgreSQL répond :

   ```powershell
   docker compose --env-file .env -f infra/docker-compose.yml exec postgres pg_isready -U air_quality -d air_quality
   ```

La base écoute sur `localhost:5432` par défaut. Les paramètres de connexion se trouvent dans `.env`; adaptez la commande de vérification si vous changez l'utilisateur ou le nom de la base.

Au premier démarrage avec un volume PostgreSQL vide, `sql/init.sql` crée les tables et index du projet. Les scripts d'initialisation PostgreSQL ne sont pas rejoués si le volume `postgres_data` existe déjà. Pour recréer la base après une modification du schéma, sauvegardez d'abord les données utiles, puis utilisez la commande de réinitialisation ci-dessous.

## Configuration

`.env.example` documente les variables nécessaires à PostgreSQL. Modifiez les valeurs dans `.env` pour votre environnement local. Le fichier `.env` est ignoré par Git : ne commitez jamais de mot de passe ou de secret réel. Les valeurs fournies dans l'exemple sont réservées au développement local.

## Arrêter et réinitialiser PostgreSQL

Arrêter les conteneurs en conservant les données :

```powershell
docker compose --env-file .env -f infra/docker-compose.yml down
```

Supprimer aussi le volume et toutes les données locales de PostgreSQL :

```powershell
docker compose --env-file .env -f infra/docker-compose.yml down --volumes
```

## Structure

- `infra/` : services locaux Docker Compose
- `src/` : code applicatif organisé par domaine
- `airflow/dags/` : futurs DAGs d'orchestration
- `tests/` : tests unitaires et d'intégration
- `docs/` : documentation du projet

## État d'avancement

- Phase de démarrage : structure du dépôt et environnement PostgreSQL local.
- Prochaines étapes : contrat des événements, simulateur IoT et ingestion Kafka.

## Développement

Le travail se fait sur des branches `feature/*`, `fix/*` ou `docs/*`, puis est intégré à `develop` par Pull Request. `main` est réservée aux versions stables. Aucun push direct vers `main`.
