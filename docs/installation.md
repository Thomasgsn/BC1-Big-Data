# Installation et exécution BC1

La chaîne principale a réellement été exécutée dans ce workspace. La chaîne a aussi été rejouée sur des volumes métier neufs dans un projet Compose isolé, en réutilisant images, CSV et poids déjà acquis ; voir [reproduction.md](reproduction.md) pour la portée et les preuves. Exécuter depuis `bc1/`. Ne jamais supprimer les volumes pour corriger un simple problème d'accès.

## Prérequis et configuration

Python 3.10–3.13 ; ici `.venv` utilise Python 3.13.18, le Python global 3.15 n'est pas supporté. Docker Desktop opérationnel, connexion pour les images/JAR et plusieurs Gio libres. Hôte 16 Go, VM mesurée environ 11,67 Gio. Ne pas cumuler entraînement, Gephi et LLM en charge pour une mesure contrôlée.

Le runtime courant HDFS est construit localement depuis Hadoop 3.4.3 et Temurin 11/Noble verrouillés. Préparer son archive avant le premier build (environ 515 Mo), sans écraser un téléchargement existant :

```bash
mkdir -p tmp/hadoop-modern
test -f tmp/hadoop-modern/hadoop-3.4.3.tar.gz || curl --fail --location https://downloads.apache.org/hadoop/common/hadoop-3.4.3/hadoop-3.4.3.tar.gz -o tmp/hadoop-modern/hadoop-3.4.3.tar.gz
```

Le build vérifie le SHA-512 verrouillé et refuse une archive différente. Signature et sources : [dossier runtime](hadoop-runtime.md). `bootstrap.py` sélectionne `docker-compose.yml:infra/hadoop-modern/migration.yml` par `COMPOSE_FILE` ; le `.env` existant a reçu uniquement cette variable publique lors de la migration, sans changer les secrets. Les commandes `docker compose` habituelles utilisent ainsi le runtime courant. Un `-f` explicite remplace cette sélection : pour un nouvel environnement isolé, inclure aussi le fichier de migration.

```bash
python3.13 -m venv .venv
make test
make bootstrap
make config
bash scripts/stack.sh up
```

L'environnement virtuel et `.env` existent déjà ici : les conserver. `bootstrap.py` crée les secrets aléatoires et les images par digest seulement si `.env` est absent, avec permissions 0600. Un changement de `.env` ne change pas les mots de passe d'une base déjà initialisée. Les migrations SQL 001–004 sont appliquées sur volume neuf ; pour un volume existant, examiner et appliquer uniquement la migration nécessaire, sans réinitialisation.

Le script de démarrage valide Compose, construit Spark/API, attend les services et HDFS hors safemode, prépare `/bc1` et crée le topic. Certains wrappers ont rencontré un refus de socket dans Codex ; les appels directs `docker compose` y fonctionnent et ont permis les essais. Ce diagnostic historique ne signifie pas que l'utilisateur doit lancer les tests à la place de l'agent.

PaySim doit être acquis et vérifié selon [dataset.md](dataset.md) : CSV `data/raw/PS_20174392719_1491204439457_log.csv`, SHA-256 `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`. PDF, données, poids et secrets ne sont pas publiés implicitement.

## Contrôle borné et flux permanent

```bash
bash scripts/stack.sh smoke
```

Le smoke utilise un run neuf, 1 000 transactions, jointure JDBC, ingestion `availableNow`, rapprochement CSV/HDFS, redémarrage Kafka/NN/DN et nouvelle lecture. Volumes conservés ; rapport local sous `docs/evidence/p2-p3/`. Ce smoke n'entraîne pas les modèles.

Pour un essai permanent, démarrer le consommateur dans un terminal et attendre `stream_ready` avant le producteur :

```bash
bash scripts/spark-job.sh ingest --run-id MON_FLUX_NEUF --starting-offsets latest --duration-seconds 150
```

Dans un second terminal :

```bash
docker compose run --rm producer --csv /project/data/raw/PS_20174392719_1491204439457_log.csv --sha256 16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b --run-id MON_FLUX_NEUF --limit 1000 --rate 50 --bootstrap-servers kafka:9092
```

Après la fin, `spark-job.sh verify --run-id MON_FLUX_NEUF --limit 1000 --csv /project/data/raw/PS_20174392719_1491204439457_log.csv` rapproche les comptes/sommes/IDs et métriques. `--starting-offsets` ne vaut que sans checkpoint ; un checkpoint existant fait autorité. La latence du rapport est émission→timestamp logique du batch, hors commit/visibilité. Ne pas changer cette définition pour annoncer un objectif atteint.

## Entraînement, graphe et scoring

Le workspace contient `runtime-v1` (préfixe 1 000) et `training-sample64-seed42` (98 813 transactions). Pour les reproduire ailleurs, choisir des runs/versions neufs et les conserver dans les commandes suivantes. Émettre un échantillon couvrant toute la période, sans utiliser le label pour sélectionner :

```bash
docker compose run --rm producer --csv /project/data/raw/PS_20174392719_1491204439457_log.csv --sha256 16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b --run-id MON_TRAIN --sample-modulus 64 --sample-seed 42 --rate 1000 --bootstrap-servers kafka:9092
bash scripts/spark-job.sh ingest --run-id MON_TRAIN --once
bash scripts/spark-job.sh train --run-id MON_TRAIN --model-version baseline-v1
bash scripts/spark-job.sh publish_graph --run-id MON_FLUX_NEUF --step-from 1 --step-to 1
bash scripts/export-graph.sh MON_FLUX_NEUF-steps-1-1
bash scripts/spark-job.sh score --run-id MON_FLUX_NEUF --training-run MON_TRAIN --model-version baseline-v1
```

Le préfixe 1 000 ne suffit pas pour entraîner : trop peu de steps/classes. Train/validation/test sont temporels, prétraitement et poids sur train, seuil et sélection sur validation, test réservé. Une version modèle existante est refusée ; rapport HDFS écrit en dernier. Un répertoire modèle sans rapport est incomplet.

Le graphe vient réellement de Mongo. Les exports refusent l'écrasement ; ne pas effacer un export pour masquer une divergence. Gephi : [procédure et résultats](gephi.md). Le rendu Toolkit, le projet portable et deux captures réelles du client Linux sont conservés dans les preuves P5.

## API et source SQL

API `http://127.0.0.1:8000/docs`, Spark `http://127.0.0.1:8080`, HDFS `http://127.0.0.1:9870`. Aucun port hôte SQL/Mongo/Kafka/Ollama. Les tokens lecteur/analyste sont dans `.env` ; les saisir uniquement dans le client local autorisé, jamais dans un rapport, capture ou commande partagée.

```bash
docker compose run --rm api-tests
docker compose run --rm administration-tests
docker compose exec -T api python tests/integration/check_api_isolation.py
```

Six tests HTTP réels ; les décisions créées sont `origin=automated_test`. Le test d'administration emploie temporairement un propriétaire dans un conteneur distinct pour une identité de test dédiée, puis la révoque ; aucun compte utilisateur modifié. L'API reçoit seulement les secrets applicatifs, pas `.env`, les propriétaires ou les jetons clients ; elle ne monte pas le dataset brut et son filesystem est read-only.

L'API crée un dossier avec `POST /v1/alerts/{id}/cases`, puis une décision avec `POST /v1/cases/{uuid}/decisions` et `Idempotency-Key` UUID. Le lecteur reçoit 403 en écriture ; quota général 60/minute/identité et génération 5/minute, 429/Retry-After. Les décisions sont immuables pour le rôle applicatif.

```bash
bash scripts/spark-job.sh extract_reviews --snapshot-id NOUVELLE_REVUE --transaction-run MON_FLUX_NEUF
```

Ce job extrait un snapshot SQL complet (100 000 revues maximum), conserve la provenance, contrôle les références HDFS et refuse l'écrasement. Ce n'est pas une CDC. Les deux revues du premier snapshot `api-review-tests-v1` sont automatisées, aucune saisie humaine n'est prétendue.

## Génération locale réelle

```bash
docker compose up -d ollama
docker compose exec -T ollama ollama pull qwen2.5:3b
docker compose run --rm --entrypoint python api-tests tests/integration/generate_draft.py
```

Le modèle doit correspondre au digest `infra/llm.lock.json`. Le tag seul ne suffit pas : une variation de poids est refusée. Qwen 3B est limité à la recherche/évaluation non commerciale ; notice/licence dans `infra/licenses/`. Aucun poids redistribué ni service payant.

Deux appels séparent conseiller et client, avec faits bornés et exemple de style déclaré. Génération pouvant prendre plusieurs dizaines de secondes sur CPU ; timeout 90 s par appel, erreur 503 explicite sans faux résultat. Les sorties font l'objet de contrôles partiels et d'une revue : brouillons uniquement, aucun SMTP. Preuves vrai/faux positif dans `docs/evidence/p7/`, labels hors prompt.

## Charge, optimisation et reprise

```bash
docker compose exec -T api python tests/integration/benchmark_sql.py
docker compose run --rm --entrypoint python api-tests tests/integration/benchmark_api.py
bash scripts/spark-job.sh benchmark_compute --expected-executors 1
docker compose up -d spark-worker-2
docker compose run --rm -e SPARK_DRIVER_PACKAGES= -e SPARK_CORES_MAX=4 spark-driver /project/src/rncp_bc1/jobs/benchmark_compute.py --expected-executors 2
docker compose stop spark-worker-2
bash scripts/spark-job.sh optimize_parquet --layout-version NOUVELLE_VERSION
```

Le benchmark SQL est synthétique en table temporaire et rollback, pas 100 000 dossiers métier. Le benchmark API consomme le quota : le lancer hors suite de quota et conserver les éventuels 429 comme erreurs mesurées. Le second worker a produit un gain faible/variable, pas une capacité doublée. L'optimisation Parquet crée une copie analytique et vérifie toutes les colonnes sans modifier curated.

Les restaurations SQL/Mongo/HDFS réellement effectuées sont décrites dans `evidence/p8/restoration.json` et les scripts `restore-check-*`. Elles ciblent des namespaces neufs sur le même hôte ; pas de restauration automatique dans les bases existantes. Le snapshot HDFS de données exclut les checkpoints et journaux FileSink à chemins absolus ; sa lecture a été contrôlée séparément. Sauvegardes hors hôte/chiffrées et restauration des modèles restent ouvertes.

Le profil `resilience` ajoute deux brokers, sans rendre ZooKeeper/HDFS/API hautement disponibles. L'essai Kafka doit utiliser un **nouveau topic isolé**, réplication 3, ISR minimal 2 et le script `tests/integration/kafka_failover.py` avec sa synchronisation `/control`. Ne pas réutiliser le topic d'un essai précédent : ses messages fausseraient les comptes. [Preuve de bascule](evidence/p8/kafka-leader-failure.json).

## Arrêt et limites

```bash
docker compose stop
docker compose up -d --wait --wait-timeout 300
docker compose up -d ollama
```

Les profils optionnels (Ollama, second worker, brokers supplémentaires) doivent être redémarrés explicitement au besoin. Le laboratoire reste HDFS simple, sans TLS/Kerberos ni HA globale. Aucun `down -v`, effacement de données ou publication n'est nécessaire à son usage ; ces actions exigent un accord distinct.


Le worker Spark possède désormais un contrôle de santé vérifiant son inscription ALIVE sur le master. Un conteneur `running` ne suffisait pas : un worker désinscrit a bloqué les jobs lors de la migration. Vérifier `docker compose ps` ; le healthcheck détecte l'état mais Docker ne redémarre pas automatiquement un conteneur seulement unhealthy. Après diagnostic et hors job actif, `docker compose restart spark-worker` a rétabli l'inscription lors de cet incident. Aucun redémarrage général ni effacement de données nécessaire.
