# BC1 — Architecture Big Data et détection de fraude

Projet de certification RNCP40875 : collecte de transactions synthétiques, stockage distribué, analyse de réseaux, détection de fraude et explications génératives.

**Développement BC1 en cours : plateforme opérationnelle, 38 tests unitaires et 6 tests API réussis.** Ingestion HDFS, publication Mongo, deux modèles MLlib et scoring réellement exécutés. Client Gephi et génération locale réellement vérifiés ; reproduction de la chaîne sur volumes métier neufs vérifiée, avec caches acquis réutilisés. Sécurité forte, HA globale et livraison finale restent ouvertes. BC2/BC3 non commencés.

## Documentation

- [Audit et exigences](docs/audit.md)[AGENTS.md](AGENTS.md)
- [Sources et limites de vérification](docs/sources.md)
- [Architecture proposée et arbitrages](docs/architecture.md)
- [Matrice C1.1 à C2.4 et exigences pédagogiques](docs/rncp-matrix.md)
- [Plan et critères d'acceptation](docs/implementation-plan.md)
- [Rapport technique](docs/technical-report.md)
- [Reproduction isolée et portée des preuves](docs/reproduction.md)
- [Progression réelle](docs/progress.md)
- [Vérifications et stratégie de tests](docs/testing.md)
- [Préparation au jury](docs/jury-preparation.md)
- [PaySim : acquisition, licence et statistiques](docs/dataset.md)
- [Environnement et versions candidates](docs/compatibility.md)
- [Runtime HDFS candidat et migration proposée](docs/hadoop-runtime.md)
- [Installation, commandes et limites réelles](docs/installation.md)
- [Procédure Gephi et preuves à produire](docs/gephi.md)

## Démarrage

Runtime HDFS actif : Hadoop 3.4.3 / Temurin 11 / Ubuntu 24.04, sélection persistante via `COMPOSE_FILE`. La configuration de base conserve l’ancien digest uniquement pour secours et historique.

Depuis `bc1/`, utiliser Python 3.10–3.13 et Docker Desktop. `.venv` existe ici sous Python 3.13.18 ; le Python global 3.15 n'est pas supporté.

```bash
make test
# Sur une installation neuve : acquérir l’archive Hadoop selon docs/installation.md.
python3.13 scripts/bootstrap.py
docker compose config --quiet
bash scripts/stack.sh up
```

Un `.env` existant est conservé ; ne jamais afficher ou versionner ses secrets. Les PDF restent dans `../.data/`, PaySim dans `data/raw/` ignoré. Les commandes et limites sont détaillées dans [installation.md](docs/installation.md) et les résultats réels dans [progress.md](docs/progress.md).

API : `http://127.0.0.1:8000/docs`, Spark : `http://127.0.0.1:8080`, HDFS : `http://127.0.0.1:9870`. Accès métier par bearer token lecteur/analyste généré localement. Les stockages et le LLM n'exposent aucun port hôte.

Le profil actuel est un laboratoire mono-hôte : HDFS simple, réplication 1, sans TLS/Kerberos ni HA globale. Une bascule de leader Kafka a été vérifiée sur un topic isolé RF3/ISR2. Les scores sont non calibrés ; le modèle LR obtient 55,22 % de rappel et 3,80 % de précision sur son test temporel. Ce résultat appelle une discussion critique, pas une promesse de détection bancaire.

## Dossier de soutenance et profils complémentaires

Thomas Gassmann, candidat seul, échéance non communiquée. [Rapport PDF](output/pdf/rapport-technique-bc1.pdf), [présentation PDF](output/pdf/soutenance-bc1.pdf), [rapport source](docs/technical-report.md), [préparation orale](docs/jury-preparation.md). Les PDF sont reconstruits hors réseau par `docker compose -f infra/documents/compose.yml run --rm render`, après construction de l'image documentaire.

Les contrôles supplémentaires [Kerberos/HTTPS, Kafka mTLS/ACL et Spark RPC](docs/security-profiles.md) et [HA HDFS](docs/hdfs-ha.md) sont exécutés dans des profils isolés. Ils ne rendent pas le principal automatiquement sécurisé ou disponible. L’audit JAR conserve 34 correspondances élevées sur l’image HDFS sécurisée. Lire les limites avant toute exposition externe.
