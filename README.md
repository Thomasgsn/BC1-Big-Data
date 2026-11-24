# BC1 — Architecture Big Data et détection de fraude

Thomas Gassmann · RNCP40875, bloc 1 · travail individuel (le sujet prévoit un binôme).

La plateforme rejoue des transactions bancaires **synthétiques** (PaySim), les stocke dans un lac de données, analyse le réseau des comptes dans Gephi, entraîne deux modèles de détection de fraude et fait rédiger par un LLM local une explication pour le conseiller et un brouillon d’email pour le client.

## Documents du rendu

| Document | Contenu |
|---|---|
| [docs/rapport.md](docs/rapport.md) | Besoin, architecture, choix, résultats, limites, correspondance RNCP |
| [Rapport PDF](output/pdf/rapport-technique-bc1.pdf) | Version PDF du rapport, générée depuis `docs/rapport.md` |
| [Support de soutenance PDF](output/pdf/soutenance-bc1.pdf) | Présentation du flux complet, de Kafka à la réponse de l’IA |
| [docs/dictionnaire.md](docs/dictionnaire.md) | Termes techniques expliqués |
| `docs/evidence/` | Preuves brutes des essais (JSON, journaux, captures) |

## Composants

| Rôle | Composant |
|---|---|
| Ingestion | Producteur Python → [Kafka](docs/dictionnaire.md#kafka) avec [ZooKeeper](docs/dictionnaire.md#zookeeper) |
| Traitement | Spark 3.5.9 (master + worker), [Structured Streaming](docs/dictionnaire.md#micro-batch), Spark SQL, [MLlib](docs/dictionnaire.md#mllib) |
| Lac de données | [HDFS](docs/dictionnaire.md#hdfs) 3.4.3, fichiers [Parquet](docs/dictionnaire.md#parquet) |
| Data Lab | MongoDB 8 (agrégats, graphe, scores, textes générés) |
| Décisions et audit | PostgreSQL 17, API FastAPI HTTPS |
| Réseau | Export CSV/GEXF puis [Gephi](docs/dictionnaire.md#gephi) 0.11.4 |
| IA générative | [Ollama](docs/dictionnaire.md#ollama) avec Qwen 2.5 3B, en local |

Le profil livré est sécurisé : [Kerberos](docs/dictionnaire.md#kerberos) pour HDFS, [mTLS](docs/dictionnaire.md#mtls) pour Kafka, RPC Spark chiffré, bases en TLS, API en HTTPS.

## Installation

Prérequis : Docker Desktop (testé avec 16 CPU et 12 Gio de RAM alloués), Compose récent, Python 3.10–3.13, accès Internet pour les images, JAR et données. Les commandes se lancent depuis `bc1/`.

1. Environnement et secrets locaux (créés hors Git, jamais affichés) :

```bash
python3.13 -m venv .venv
.venv/bin/python scripts/bootstrap.py
```

2. Données PaySim (licence CC BY-SA 4.0, ~470 Mo), puis contrôle de l’empreinte :

```bash
mkdir -p data/raw
curl -L --fail --retry 2 --max-time 600 'https://www.kaggle.com/api/v1/datasets/download/ealaxi/paysim1?datasetVersionNumber=2' -o data/raw/paysim-v2.zip
PYTHONPATH=src python3 -m rncp_bc1.dataset extract --archive data/raw/paysim-v2.zip --destination data/raw
make profile
```

SHA-256 attendu du CSV : `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.

3. Archive Hadoop (le build vérifie son SHA-512) :

```bash
mkdir -p tmp/hadoop-modern
test -f tmp/hadoop-modern/hadoop-3.4.3.tar.gz || curl --fail --location https://downloads.apache.org/hadoop/common/hadoop-3.4.3/hadoop-3.4.3.tar.gz -o tmp/hadoop-modern/hadoop-3.4.3.tar.gz
```

4. Construction et démarrage du profil sécurisé :

```bash
docker compose -f infra/hadoop-modern/compose.yml build namenode
docker compose -f infra/secure-hdfs/compose.yml build namenode
docker compose -f infra/certification/maintenance.yml build
bash scripts/certification.sh connectors
bash scripts/certification.sh config
bash scripts/certification.sh up
bash scripts/certification.sh ca
```

L’API répond sur https://127.0.0.1:8443 avec la CA locale exportée dans `exports/certification-ca.crt` :

```bash
curl --cacert exports/certification-ca.crt https://127.0.0.1:8443/health/ready
```

## Faire tourner le flux complet

Choisir un identifiant de run neuf (`MON_RUN`). Dans un premier terminal, démarrer le streaming et attendre l’événement `stream_ready` :

```bash
bash scripts/certification.sh driver /project/src/rncp_bc1/jobs/ingest.py --run-id MON_RUN --base hdfs://namenode.bc1.test:8020/bc1/private --bootstrap-servers broker:9093 --topic secure.transactions --starting-offsets latest --duration-seconds 120 --observe-visible
```

Dans un second terminal, envoyer 1 000 transactions :

```bash
bash scripts/certification.sh producer --csv /project/data/raw/PS_20174392719_1491204439457_log.csv --sha256 16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b --run-id MON_RUN --limit 1000 --rate 50 --bootstrap-servers broker:9093 --topic secure.transactions
```

Puis rapprocher avec le CSV, publier le graphe dans MongoDB et scorer :

```bash
bash scripts/certification.sh driver /project/src/rncp_bc1/jobs/verify.py --run-id MON_RUN --base hdfs://namenode.bc1.test:8020/bc1/private --limit 1000 --csv /project/data/raw/PS_20174392719_1491204439457_log.csv
bash scripts/certification.sh driver /project/src/rncp_bc1/jobs/publish_graph.py --run-id MON_RUN --step-to 1 --base hdfs://namenode.bc1.test:8020/bc1/private
bash scripts/certification.sh driver /project/src/rncp_bc1/jobs/score.py --run-id MON_RUN --training-run MON_TRAIN --model-version baseline-v1 --base hdfs://namenode.bc1.test:8020/bc1/private
```

`MON_TRAIN` désigne un run d’entraînement. Sur une installation neuve, en créer un : rejouer sans `--limit` avec `--sample-modulus 64 --sample-seed 42`, ingérer avec `--once --starting-offsets earliest`, puis :

```bash
bash scripts/certification.sh driver /project/src/rncp_bc1/jobs/train.py --run-id MON_TRAIN --model-version baseline-v1 --base hdfs://namenode.bc1.test:8020/bc1/private
```

Variante à historique destinataire (voir le rapport) : rejouer avec `--sample-modulus 16 --sample-key destination`, puis entraîner avec `--feature-set destination_history`. `score.py` accepte ce modèle : il recalcule l’historique des destinataires à partir du run d’entraînement.

**Gephi** : dans le service mongo, `mongosh --nodb --quiet --file /scripts/export.js` avec `BC1_SNAPSHOT_ID` et `BC1_EXPORT_FILE=/exports/mongo/SNAPSHOT.json`, puis :

```bash
PYTHONPATH=src .venv/bin/python -m rncp_bc1.graph_export --input exports/mongo/SNAPSHOT.json --destination exports/gephi/NOUVEL_EXPORT
```

**IA générative** : les poids Qwen 2.5 3B (licence de recherche non commerciale, `infra/licenses/`) doivent être présents dans le volume `rncp-bc1_ollama-models`. Sur une installation neuve : `docker compose up -d ollama` puis `docker compose exec -T ollama ollama pull qwen2.5:3b`. Ensuite :

```bash
bash scripts/certification.sh genai
```

## Tests

```bash
make test
docker compose --env-file .env -f infra/certification/compose.yml build browser-tests
bash scripts/certification.sh tests
```

`make test` : 45 tests unitaires. `certification.sh tests` : refus TLS/authentification, tests HTTP de l’API et parcours navigateur ; ils demandent des scores et un graphe déjà produits.

## Livrables générés

Le rapport PDF et le support sont reconstruits hors réseau :

```bash
docker compose -f infra/documents/compose.yml run --rm render
```

Le rapport PDF est produit depuis `docs/rapport.md`, le support depuis `docs/presentation.json`.

Archive de remise : `python3 scripts/check-delivery.py` (contrôle des secrets et des liens), puis `python3 scripts/package-delivery.py`. Elle contient les fichiers suivis ou non ignorés par Git, sans `.env`, données, volumes, `tmp/` ni secrets ; une archive existante n’est jamais écrasée.

## Usage de l’IA

J’ai utilisé des assistants d’IA générative (Codex, puis Claude pour les derniers ajouts et la relecture) pour la réécriture des textes, la recherche et le sourçage des références et l’aide au développement. Les résultats cités viennent des exécutions du projet et renvoient à `docs/evidence/`. Cet usage est distinct du LLM du démonstrateur.

## Limites principales

- Données synthétiques : aucun résultat ne vaut performance bancaire réelle.
- Un seul hôte : la haute disponibilité de HDFS et de Kafka est testée dans des profils séparés, pas dans le profil sécurisé.
- Avis de vulnérabilité sans correctif, dont une correspondance critique libxml2 dans l’image PostgreSQL.
- Les textes générés sont des brouillons à relire ; aucun email n’est envoyé.
