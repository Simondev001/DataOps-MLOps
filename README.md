# Air Quality DataOps/MLOps

Plateforme universitaire de surveillance de la qualité de l'air. Le dépôt est au démarrage : cette première configuration lance PostgreSQL en local et prépare l'environnement Python. Kafka, Spark, Airflow, MLflow, l'API et le dashboard seront ajoutés dans les phases suivantes.

## Prérequis

- Git
- Python 3.11 ou plus récent
- Docker Desktop avec Docker Compose v2

Vérifier les installations :

```powershell
py --version
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
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install --upgrade pip
   py -m pip install -r requirements.txt
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

- Phase 1 : générateur IoT, contrat JSON et tests de validation réalisés.
- À poursuivre en phase 1 : Kafka, traitement/validation du flux, détection d'anomalies et stockage des mesures dans PostgreSQL.
- Phases suivantes : orchestration Airflow, cycle de vie MLflow, API de prédiction, catalogue et tableaux de bord.

## Développement

Le travail se fait sur des branches `feature/*`, `fix/*` ou `docs/*`, puis est intégré à `develop` par Pull Request. `main` est réservée aux versions stables. Aucun push direct vers `main`.

## Simulateur IoT

Le module `src/ingestion/sensor_generator.py` génère des capteurs autour d'Agadir
et leurs événements JSON Lines. Chaque événement respecte le contrat du sujet :

- `sensor_id` : identifiant du capteur ;
- `timestamp` : date ISO 8601 en UTC ;
- `location` : objet avec `lat` et `lon` ;
- `measurements` : `pm2_5`, `pm10`, `no2`, `o3` (µg/m³), `temperature` (°C) et `humidity` (%) ;
- `status` : `active` pour les événements émis.

Les valeurs suivent des variations journalières et des pics de pollution sont
simulés occasionnellement. Le générateur ignore les capteurs inactifs. Pour
respecter ce contrat, le consommateur devra décomposer `measurements` avant
l'insertion dans `air_quality_measurements` ; `timestamp` correspond à la
colonne SQL `measured_at`, et `location` aux coordonnées du capteur.

Depuis la racine du dépôt, lancer la capture simulée :

```powershell
py -m src.ingestion.sensor_generator --sensors 5 --events-per-sensor 10 --interval-seconds 60
```

La commande écrit un événement JSON par ligne dans la sortie standard. Pour
lancer les tests du projet :

```powershell
py -m pytest -q
```

`validate_event(event)` vérifie le contrat. Les fonctions `generate_event`,
`generate_events` et `simulate_capture` sont importables pour l'intégration.