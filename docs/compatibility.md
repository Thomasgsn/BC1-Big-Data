# Faisabilité et versions — P1

## État d'exécution actuel

Les appels directs `docker compose` fonctionnent. Les constats d'accès refusé ci-dessous sont historiques. Exécutés avec succès : Kafka→Spark→HDFS, jointure JDBC SQL, Mongo Spark, MLlib LR/RF, export et statistiques Gephi Toolkit. Versions relevées : Spark 3.5.8, Scala 2.12, Java 17.0.17, Python conteneur 3.10.12, PostgreSQL 17.12, MongoDB 8.0.38 ; local Python 3.13.18. VM Docker : `/proc/meminfo` 12 242 320 Kio, 16 vCPU annoncés (pas les cœurs physiques du Mac). Worker de démonstration limité à 2 cœurs et 1 536 Mio Spark.

NumPy 2.2.6 ajouté avec hashes à l'image Spark ; l'extraction du vecteur ML utilise le pont Scala public pour éviter un import pandas/Arrow inutile. Sonde Dense/Sparse réellement passée. API Python 3.12, FastAPI/psycopg/PyMongo/Uvicorn verrouillés avec hashes dans `requirements-api.lock`. Gephi Toolkit 0.11.4/Maven 3.9.9/Java 17 : 150 JAR téléchargés et empreintes enregistrées ; ce relevé n'est pas un audit de vulnérabilité ni une signature de confiance.

LLM : Qwen 1.5B essayé mais sorties non conformes ; Qwen 3.1B Q4_K_M acquis, digest dans `infra/llm.lock.json`, licence **Qwen Research (recherche/évaluation non commerciale)**, distincte de l'Apache 2.0 du 1.5B. Notice et licence présentes dans `infra/licenses/`. Aucun poids redistribué ni service commercial créé. Les premiers brouillons non conformes ont été rejetés et conservés. Des sorties réelles v6 puis v7 ont ensuite passé les contrôles sur vrai et faux positif ; une revue humaine reste nécessaire. Limite mémoire Ollama portée de 3 à 4 Gio après pression cgroup observée (sans OOM kill) ; contexte 2 048, batch 64, deux threads.

Audit Python exécuté le 18 novembre avec pip-audit 2.10.1 : API 18 dépendances, zéro avis connu ; runtime deux avis distincts sur kafka-python 2.3.1. Correction 2.3.2, roue vérifiée par SHA, image reconstruite, deux tests parseur/SCRAM passés localement et en conteneur, nouvel audit sans avis connu. Voir [la synthèse](evidence/p8/dependency-security-summary.json). Les rapports initiaux sont conservés : ne pas confondre absence d'avis connu et sécurité garantie.

Les scans OS/JAR/images et la sécurisation forte restent ouverts ; les images ne sont pas qualifiées de sûres pour exposition publique.

## Runtime HDFS actuel

Hadoop 3.4.3 / Temurin 11.0.33 / Ubuntu 24.04.5 déployé sur le principal après tests isolés et copie cohérente ; [journal de bascule](evidence/p8/hadoop-modern/deployment.json). Le constat CentOS 7/OpenJDK 1.8.0_212 concerne l'image historique 3.4.2. Spark reste sous Java 17, avec client Hadoop 3.3.4. Les commandes ordinaires chargent `migration.yml` par `COMPOSE_FILE`. Le catalogue `images.lock.json` conserve les images externes initiales ; le runtime construit localement et ses empreintes sont décrits par `infra/hadoop-modern/lock.json`. Le diagnostic `check_environment.py --probe-images` sonde ce catalogue historique, pas les services en cours ; pour le runtime actif, utiliser `docker compose exec -T namenode hdfs version` et `java -version`.

## Constats historiques au cadrage


Docker Desktop a été lancé par `open -a Docker`. Le socket est ensuite présent mais l'exécution Codex reçoit `permission denied`. Le 17 novembre 2026, l'utilisateur a transmis le résultat réussi de `docker run --rm hello-world` depuis son terminal : image amd64, digest `sha256:1e4c05b897a751332ce85c7e9449da2d93514ea2dea6dbb0e2753c9e949b2bfa`. Cette preuve est déclarative utilisateur ; ce n'est pas un test de conteneur exécuté par Codex. Les ressources effectivement allouées à la VM Docker restent à relever.

`/Applications/Gephi.app` n'a pas été trouvé. Ce contrôle ne suffit pas à exclure une installation située ailleurs ; la procédure d'import et les algorithmes Gephi restent non testés. Ollama est présent dans le PATH, aucun modèle n'a été téléchargé ni lancé.

## Images candidates épinglées

[images.lock.json](../infra/images.lock.json) contient les références complètes avec digest, plateformes et URLs des métadonnées Docker Hub consultées. Le statut `metadata_verified_runtime_unverified` signifie : tags/digests repérés, **pas** compatibilité fonctionnelle validée.

| Composant | Candidat | État |
|---|---|---|
| Kafka | Apache 3.9.2 | Image amd64/arm64 disponible ; version classée dans les versions archivées sur la page Apache, risque de maintenance explicite |
| Spark | Apache 3.5.8, Scala 2.12, Java 17, Python 3 | Image amd64/arm64 disponible ; Python précis et bibliothèques Hadoop à relever dans l'image |
| Hadoop | Apache 3.4.2 | Image amd64 repérée, adaptée à l'architecture hôte ; Java et compatibilité protocole HDFS à tester |
| PostgreSQL | Branche 17, variante bookworm | Digest capturé depuis le tag ; version patch à relever dans le conteneur |
| MongoDB | Branche 8.0 | Digest capturé depuis le tag ; version patch à relever dans le conteneur |

Les tags de branche SQL/Mongo ne sont pas utilisés seuls : leur digest fixe le contenu acquis, même si le tag évolue ensuite. Les licences, scans de vulnérabilité, démarrages et tests croisés restent à vérifier ; ces candidats ne sont pas déclarés sûrs pour une exposition publique.

Sources primaires : [images Apache Spark](https://hub.docker.com/r/apache/spark), [Kafka](https://hub.docker.com/r/apache/kafka), [Hadoop](https://hub.docker.com/r/apache/hadoop), [versions Kafka](https://kafka.apache.org/community/downloads/), [Spark 3.5.8](https://spark.apache.org/docs/3.5.8/). Kafka 3.9.2 est retenu provisoirement pour ZooKeeper demandé dans le sujet. Une migration de famille devra préserver l'exigence pédagogique ou faire l'objet d'un accord explicite de l'enseignant.

## Connecteurs à tester

- Spark Kafka : `org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8`, selon le [guide officiel versionné](https://spark.apache.org/docs/3.5.8/structured-streaming-kafka-integration.html).
- MongoDB Spark : candidat 10.7.0 / Scala 2.12 ; la [documentation 10.x](https://www.mongodb.com/docs/spark-connector/v10.x/) indique Spark 3.2–3.5 et MongoDB 4.2 ou ultérieur. Une compatibilité annoncée n'est pas une intégration testée.
- PostgreSQL JDBC : `org.postgresql:postgresql:42.7.14`, version publiée sur la [page officielle pgJDBC](https://jdbc.postgresql.org/download/) et Maven Central lors du contrôle. Sonde de jointure SQL implémentée, pas encore exécutée.

## Diagnostic à exécuter depuis le terminal qui accède à Docker

```bash
cd /Users/thomasgassmann/Documents/ecole/rncp/bc1
python3 scripts/check_environment.py --probe-images
```

Le script enregistre les ressources Docker et sonde les binaires des cinq images par digest. Il télécharge les images manquantes, crée uniquement des conteneurs éphémères plafonnés à 1 Go et sans réseau pour les sondes ; aucun service persistant, volume ou secret créé. Il ne modifie pas Docker Desktop et ne supprime aucune donnée. Résultat dans `docs/evidence/p1/environment-terminal.json` ; le code retour est non nul si une sonde échoue. Le rapport évite d'enregistrer les paramètres privés de `docker info`.

Ce diagnostic ne remplace pas le critère P1.3 : un job Spark doit encore consommer Kafka, écrire/relire Parquet dans HDFS et joindre SQL. Les configurations Compose définitives ne seront figées qu'après ce test. Le blocage d'accès Docker concerne les essais, pas les outils de profilage PaySim déjà exécutés.


## Reprise via Compose

L’appel direct `docker compose ps` a réussi depuis Codex, puis `docker compose up -d --build --wait --wait-timeout 300` a commencé les téléchargements et le build. Les refus de socket précédents restent consignés comme diagnostics historiques ; ils ne constituent plus un blocage absolu. Le démarrage et les sondes fonctionnelles sont en cours, sans réussite présumée.

Les trois JAR top-level Kafka/Mongo/JDBC ont été téléchargés depuis Maven Central, ouverts comme archives ZIP avec contrôle CRC et empreintes SHA-256 conservées dans `infra/connectors.lock.json`. Pas de vérification de signature ni d’inventaire complet des dépendances transitives à ce stade.

Sources d’implémentation Hadoop vérifiées : [Dockerfile officiel branche docker-hadoop-3.4.2](https://raw.githubusercontent.com/apache/hadoop/docker-hadoop-3.4.2/Dockerfile) et [Compose de la même branche](https://raw.githubusercontent.com/apache/hadoop/docker-hadoop-3.4.2/docker-compose.yaml). Le profil BC1 utilise ses propres XML et une entrée explicite sans reformater les volumes existants.
