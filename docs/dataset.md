# PaySim — acquisition et profilage réels

Source : [Synthetic Financial Datasets For Fraud Detection](https://www.kaggle.com/datasets/ealaxi/paysim1), ealaxi / Edgar Alonso Lopez-Rojas. Version acquise : **2**. Les métadonnées officielles Kaggle indiquent **CC BY-SA 4.0** ; elles sont conservées dans [paysim-source.json](evidence/p1/paysim-source.json).

Attribution demandée par l'auteur : E. A. Lopez-Rojas, A. Elmir et S. Axelsson, *PaySim: A financial mobile money simulator for fraud detection*, EMSS, Larnaca, 2016. Le CSV acquis n'a pas été modifié. Le profil est une analyse descriptive calculée par le projet ; les données demeurent synthétiques. Conserver attribution et [lien de licence](https://creativecommons.org/licenses/by-sa/4.0/) avec toute redistribution de données ou adaptation concernée ; la licence du simulateur ne remplace pas celle du dataset. Aucun jeu de données n'est publié par ce travail.

## Résultats mesurés

Rapport intégral : [paysim-profile.json](evidence/p1/paysim-profile.json). Il résulte de la lecture de **toutes** les lignes, pas d'un échantillon.

| Indicateur | Résultat |
|---|---|
| Taille CSV | 493 534 783 octets |
| Transactions | 6 362 620 |
| Fraudes, `isFraud=1` | 8 213, soit environ 0,1291 % |
| Alertes historiques, `isFlaggedFraud=1` | 16 |
| Steps | 1 à 743 inclus, 743 valeurs distinctes, aucun retour en arrière observé |
| Montant | 0 à 92 445 516,64 en unité monétaire locale non précisée |
| Montants nuls | 16 ; conservés comme observations, pas supprimés automatiquement |
| Décimales maximum du montant | 2 |
| Champs vides / absents | 0 sur les 11 colonnes |
| Lignes invalides selon les contrôles implémentés | 0 |

Types : CASH_IN 1 399 284 ; CASH_OUT 2 237 500 ; DEBIT 41 432 ; PAYMENT 2 151 495 ; TRANSFER 532 909. Les fraudes sont étiquetées CASH_OUT pour 4 116 lignes et TRANSFER pour 4 097. Ce constat ne permet pas de conclure que tous les autres types seraient sans risque en production.

Empreinte SHA-256 de l'archive : `f7eef9ffad5cfa64a034143a5c9b30491d189420b273d5ad5723ca40b596613d`.

Empreinte SHA-256 du CSV : `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`.

Ces empreintes identifient les fichiers acquis ; aucune empreinte signée fournie par l'auteur n'a été vérifiée. L'extraction a contrôlé le CRC ZIP et la taille annoncée. Les données locales sont ignorées par Git.

## Décisions de préparation

- Le profilage confirme des montants représentables en `Decimal(18,2)` pour ce fichier ; les dépassements resteront contrôlés à l'ingestion.
- Un `step` représente une heure selon l'auteur. Ne pas transformer la mention descriptive « 744 steps / 30 jours » en maximum réellement observé : ce fichier se termine au step 743. Aucun horodatage intrahoraire n'est fourni.
- Conformément à l'avertissement de l'auteur, **exclure les quatre soldes** (`oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest`) des prédicteurs : les annulations de fraude modifient ces colonnes. Exclure également les deux labels. Les soldes restent stockés pour l'audit.
- Le déséquilibre mesuré impose une évaluation rappel/précision et PR-AUC en complément d'AUC-ROC. Un classificateur toujours négatif aurait une exactitude trompeusement élevée.
- Les montants nuls et les valeurs nulles de solde ne sont pas des champs manquants ; ne pas les imputer aveuglément. L'absence d'information de solde pour certains marchands est décrite par l'auteur.
- Aucun contrôle d'unicité par contenu ou analyse de graphe n'a encore été exécuté. L'absence d'anomalie de format n'est pas une preuve de qualité métier parfaite.

## Reproduction depuis `bc1/`

Python 3.11 à 3.13 ; les outils de profilage utilisent uniquement la bibliothèque standard, sans téléchargement de dépendance.

```bash
mkdir -p data/raw
curl -L --fail --retry 2 --max-time 600 \
  'https://www.kaggle.com/api/v1/datasets/download/ealaxi/paysim1?datasetVersionNumber=2' \
  -o data/raw/paysim-v2.zip
PYTHONPATH=src python3 -m rncp_bc1.dataset extract \
  --archive data/raw/paysim-v2.zip --destination data/raw
make profile
make test
```

Ne pas relancer le téléchargement sur une archive déjà acquise sans vérifier son état ; curl écrase son fichier de destination. L'extracteur refuse pour sa part d'écraser un CSV existant. Si le CSV est déjà présent, relancer seulement `make profile` pour recalculer son empreinte et ses statistiques.

La commande `profile` retourne 0 si le fichier a été contrôlé sans ligne invalide, 1 si le rapport contient des lignes invalides, 2 en cas d'erreur d'accès, d'en-tête ou de fichier vide. Les sorties sont structurées en JSON ; le rapport est écrit atomiquement pour préserver un résultat antérieur en cas d'erreur de sérialisation.
