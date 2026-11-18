# Sources du cadrage

Lecture et vérifications : 17 novembre 2026. La pagination ci-dessous correspond aux pages physiques des PDF fournis. Les empreintes SHA-256 des cinq fichiers sont conservées dans [source-manifest.json](source-manifest.json).

## Documents fournis

| ID | Document | Pages et utilisation |
|---|---|---|
| INFO | [Document d'information RNCP40875](../../.data/Document%20d’information%20RNCP40875%20-%20Expert%20en%20ingénierie%20des%20données.pdf) | 5 pages lues ; p. 3–4 pour modalités BC1, groupe, rapport et jury ; pondération 40/60 présentée comme cadre d'appréciation |
| REF | [Référentiel Expert Ingénierie de données](../../.data/Référentiel%20Expert%20Ingénierie%20de%20données.pdf) | 25 pages lues ; analyse BC1 détaillée p. 2–6 ; p. 25 pour anglais technique et présentation orale |
| SUJET | [Projet Hadoop/Spark BC1](../../.data/Projet_Hadoop_Spark_Validation_Bloc1.pdf) | 3 pages lues ; exigences techniques p. 1–2, démonstration p. 3 |
| BC2 | [Projet Analyse des données](../../.data/Projet%20Analyse%20des%20données%20-%20Validation%20Bloc2.pdf) | 4 pages lues pour délimiter les blocs ; aucune architecture ni planification de ce bloc |
| BC3 | [Projet cloud](../../.data/Projet_cloud_Validation_Bloc3.pdf) | 5 pages lues pour délimiter les blocs ; aucune architecture ni planification de ce bloc |

Extraction par `pdfplumber`, avec repères de page ; rendus des 3 pages du sujet et des 5 pages BC1 du référentiel inspectés en planche pour contrôler la structure des tableaux. Intermédiaires dans `/tmp/rncp-audit`, non nécessaires à la reprise. Aucun PDF manquant ; aucun besoin d'ajout de support identifié.

## Sources externes primaires

- [Auteur de PaySim](https://github.com/EdgarLopezPhD/PaySim) : décrit le simulateur, l'origine synthétique des données, référence le dataset Kaggle et l'article de 2016. Le code du simulateur affiche GPL-3.0 ; cela ne prouve pas la licence du dataset.
- [Dataset Kaggle recommandé](https://www.kaggle.com/datasets/ealaxi/paysim1) : page repérée, mais contenu non lisible par l'outil web. Lors du cadrage : aucun téléchargement réussi ou contrôle de licence effectué. La requête de métadonnées avec curl n'a produit aucun fichier exploitable. Le compte éventuellement requis, la version et les conditions doivent être vérifiés lors de l'acquisition.
- [Guide Kafka 3.9](https://kafka.apache.org/39/getting-started/quickstart/) : confirme le fonctionnement avec ZooKeeper. Justifie une famille candidate compatible avec le sujet, sans présumer son niveau de maintenance en novembre 2026.
- [Structured Streaming Spark 3.5.6](https://spark.apache.org/docs/3.5.6/structured-streaming-programming-guide.html) : sémantiques de reprise, micro-batch, mode continu et limites des sorties. Référence de conception, pas version finale validée.
- [HDFS HA avec QJM](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HDFSHighAvailabilityWithQJM.html) : le lien `stable` consulté présente Hadoop 3.3.5 ; utiliser une URL versionnée lors du verrouillage effectif.

Les descriptions locales paraphrasent les sources ; les objectifs chiffrés proposés sont des choix d'ingénierie, jamais des seuils RNCP. Les technologies, images et connecteurs finaux devront être revérifiés au premier jalon. Voir les résultats actualisés de P1 ci-dessous. La fiche publique RNCP40875 a été repérée sur France compétences ; ce cadrage s'appuie sur les critères détaillés du REF fourni, sans revendiquer une comparaison exhaustive avec ses éventuelles révisions en ligne.


## Mise à jour P1 après validation

L'API publique Kaggle a fourni les métadonnées officielles et l'archive version 2 a été téléchargée. Les réserves d'accès du cadrage ci-dessus sont historiques, non des blocages actuels du dataset. [Métadonnées sauvegardées](evidence/p1/paysim-source.json), [profilage complet](evidence/p1/paysim-profile.json) et [procédure/attribution](dataset.md).

Endpoints utilisés : [description officielle](https://www.kaggle.com/api/v1/datasets/view/ealaxi/paysim1) et [archive versionnée](https://www.kaggle.com/api/v1/datasets/download/ealaxi/paysim1?datasetVersionNumber=2). Source de licence : champ `licenseName` de ces métadonnées. La consigne d'exclusion des quatre soldes provient de la description de l'auteur.

Les versions et sources techniques P1 sont regroupées dans [compatibility.md](compatibility.md), avec les digests relevés sur Docker Hub. Le téléchargement et le profilage PaySim ont réussi après une première tentative en échec DNS ; aucune donnée fictive n'a remplacé le fichier.
