# Dictionnaire BC1

Termes utiles pour comprendre et défendre le projet. Chaque entrée : définition, rôle ici, exemple si besoin.

## Kafka

Journal de messages distribué : des producteurs écrivent, des consommateurs lisent à leur rythme.
Ici : reçoit les transactions envoyées par le producteur Python et les garde pour que Spark puisse les relire.
Exemple : si Spark s’arrête, il reprend à la dernière position (offset) qu’il avait validée.

## ZooKeeper

Service de coordination qui garde l’état partagé d’un cluster.
Ici : exigé par le sujet pour Kafka ; les versions récentes de Kafka peuvent s’en passer (mode KRaft).

## HDFS

Système de fichiers distribué de Hadoop, fait pour de gros fichiers lus en bloc.
Ici : lac de données qui contient les transactions brutes et nettoyées, les rejets, les checkpoints et les modèles.

## Parquet

Format de fichier qui range les données par colonne.
Ici : format des transactions dans HDFS ; une requête sur le montant ne lit que la colonne montant.

## Micro-batch

Traitement par petits lots à intervalle fixe, plutôt que message par message.
Ici : Spark Structured Streaming traite les nouveaux messages toutes les 5 secondes ; ce n’est pas du traitement continu événement par événement.

## MLlib

Bibliothèque d’apprentissage automatique de Spark.
Ici : entraîne et compare la régression logistique et le Random Forest.

## Gephi

Logiciel de visualisation et d’analyse de graphes.
Ici : importe les comptes (nœuds) et transactions (arêtes) exportés de MongoDB, puis calcule degré et modularité.

## Degré

Nombre de liens d’un nœud. Le degré entrant compte les flèches qui arrivent.
Ici : un compte avec un degré entrant de 23 reçoit de l’argent de 23 transactions ; c’est un « hub » à examiner, pas une preuve de fraude.

## Modularité

Mesure (au plus 1) de la séparation d’un graphe en communautés : plus elle est proche de 1, plus les groupes sont nets.
Ici : 0,995, mais seulement parce que le graphe est fait de 597 morceaux déconnectés.

## Fuite de cible

Erreur où une variable du modèle contient, directement ou non, la réponse à prédire.
Ici : les soldes PaySim trahissent la fraude ; ils sont exclus des variables.

## Découpage temporel

Séparation des données par date : on apprend sur le passé, on teste sur le futur.
Ici : apprentissage jusqu’au step 281, validation jusqu’au 355, test après. Cela imite l’usage réel.

## Rappel et précision

Rappel : part des vraies fraudes détectées. Précision : part des alertes qui sont de vraies fraudes.
Exemple : rappel 53 % et précision 23 % signifient qu’on trouve un peu plus d’une fraude sur deux et qu’une alerte sur quatre environ est justifiée.

## PR-AUC

Aire sous la courbe précision-rappel, de 0 à 1. Plus adaptée que la ROC-AUC quand les fraudes sont rares.
Ici : 0,249 pour le meilleur modèle ; un modèle au hasard ferait environ 0,003.

## Kerberos

Protocole d’authentification par tickets délivrés par un serveur central (KDC).
Ici : chaque processus prouve son identité pour accéder à HDFS.

## mTLS

TLS mutuel : le client et le serveur présentent chacun un certificat.
Ici : seuls le producteur et Spark, munis de leurs certificats, peuvent écrire ou lire dans Kafka.

## Haute disponibilité

Capacité à continuer de fonctionner quand un composant tombe.
Ici : testée sur Kafka (3 réplicas) et HDFS (deux NameNodes avec bascule automatique), dans des profils séparés.

## Ollama

Outil qui fait tourner un modèle de langage sur la machine locale.
Ici : exécute Qwen 2.5 3B pour rédiger l’explication et le brouillon d’email, sans envoyer de données à l’extérieur.
