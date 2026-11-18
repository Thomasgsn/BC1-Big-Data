# Audit BC1

## État initial constaté

Le dossier ne contient que `.data/` (cinq PDF) et `.idea/` (configuration IDE). `git status --short` répond « not a git repository ». Aucun code, dépendance de projet, convention applicative, test ou infrastructure existant à préserver. Aucun `AGENTS.md` trouvé dans le dossier ou ses ancêtres. Après audit, le cadrage est placé dans `bc1/`, avec sa propre documentation et configuration. Le cadrage ajoute uniquement de la documentation et des fichiers préparatoires ; aucun développement n'est commencé.

L'environnement réel et les commandes de diagnostic sont consignés dans [testing.md](testing.md). La lecture mémoire annonce 16 Go, l'architecture hôte est x86_64. Les informations CPU sont indicatives car `system_profiler` émet des avertissements d'accès à sysctl. Docker CLI et Compose sont présents ; le moteur est indisponible. La présence de `/usr/bin/java` ne correspond pas à un runtime Java installé. Gephi, les images et les connecteurs n'ont pas été vérifiés.

## Hiérarchie et divergences

Les références abrégées renvoient à [sources.md](sources.md). REF définit les compétences ; SUJET définit le travail pédagogique demandé ; INFO précise l'organisation annoncée. En cas d'écart, conserver les deux obligations et demander une clarification à l'enseignant ; aucune équivalence n'est présumée.

| Point | Constat | Conséquence BC1 |
|---|---|---|
| Relationnel | REF C1.1 impose une base normalisée et des tests de charge ; SUJET cite seulement un Data Lab NoSQL | Ajouter PostgreSQL pour dossiers d'investigation, revues analystes et audit |
| API | REF C2.1 impose API, authentification, autorisations et quotas ; SUJET ne les précise pas | Ajouter une API REST documentée et testée |
| Variété | REF C1.3/C2.3/C2.4 demande des sources variées ; rejouer le même CSV en JSON ne crée pas une seconde source indépendante | Intégrer les décisions analystes réellement saisies dans PostgreSQL ; portée pédagogique de cette variété à confirmer |
| Résilience | Un broker, un NameNode, un DataNode et un worker satisfont la topologie minimale du SUJET mais pas une démonstration complète C1.4 | Profil de développement puis essais répliqués et de bascule ; environnement HA à résoudre |
| Temps réel | REF C2.2 distingue micro-batch et traitement au fil de disponibilité | Flux permanent à faible délai mesuré ; ne pas présenter le micro-batch comme un moteur continu événement par événement ; clarification si ce dernier est exigé |
| ZooKeeper | SUJET le demande explicitement ; architecture Kafka moderne à examiner au verrouillage | Retenir une famille Kafka compatible ZooKeeper ; toute substitution KRaft doit être acceptée pédagogiquement |
| IA | MLlib et GenAI sont obligatoires dans SUJET BC1 bien que REF situe les compétences IA spécifiques dans BC2 | Les réaliser dans BC1 sans démarrer le projet BC2 ni prétendre le valider |
| Évaluation | SUJET : binôme et note module ; REF : formatif puis rapport et jury ; INFO : groupe, 40/60 indicatif | Préparer contributions individuelles et soutenance ; confirmer calendrier, format rapport et grille auprès de l'école |
| Communication | SUJET demande de rédiger un email personnalisé ; aucune obligation explicite de l'envoyer | Produire un brouillon avec alias de compte synthétique, sans inventer identité ni adresse client |

## Obligations du sujet

- SUJET p. 1 : Docker Compose ; Kafka avec ZooKeeper et broker ; HDFS NameNode/DataNode ; Spark Master/Worker avec PySpark et Spark SQL ; MongoDB **ou** Cassandra ; Gephi client.
- SUJET p. 1–2 : producteur JSON, consommation Spark, typage/nettoyage et Parquet HDFS ; métriques de volume par minute et montant total par type.
- SUJET p. 2 : agrégats HDFS vers NoSQL ; nœuds/comptes et arêtes/transactions ; export depuis NoSQL ; modularité et degré dans Gephi avec interprétation.
- SUJET p. 2 : variables explicatives, comparaison régression logistique/Random Forest MLlib ; AUC, matrice de confusion, rappel.
- SUJET p. 2 : appel effectif à un LLM local ou API ; métadonnées et motifs de risque ; explication conseiller et brouillon client rassurant demandant validation dans l'application.
- SUJET p. 2–3 : dépôt GitHub contenant Compose et scripts Spark, rapport justifiant l'architecture avec performances IA et captures Gephi, vidéo ou présentation du flux complet.

Le choix PaySim est **recommandé**, et un générateur Python de transactions est **autorisé** (SUJET p. 1). MongoDB/Cassandra et LLM local/API sont des alternatives, pas des obligations cumulatives. GPT-4o et Llama 3 sont des exemples. Les exemples de features ne constituent pas une liste imposée. Aucun volet BC1 n'est désigné facultatif ; l'IA générative facultative du sujet BC2 ne s'applique pas ici.

## Exigences complémentaires du référentiel

La [matrice](rncp-matrix.md) détaille C1.1 à C2.4, y compris intégrité, tests de charge SQL, semi-structuré/non structuré, sécurité du lac, KPI de latence/capacité/vitesse, haute disponibilité, quotas API, veille et optimisation comparative. L'accessibilité universelle impose de prévoir une documentation claire, des sorties exploitables et une consultation accessible : elle ne signifie pas exposer publiquement les bases. REF p. 25 mentionne aussi anglais technique et prise de parole ; préparer un glossaire anglais et une explication orale des choix, sans inventer un format d'épreuve.

## Risques et dépendances

| Risque | Impact / niveau | Traitement prévu et condition de levée |
|---|---|---|
| 16 Go pour JVM multiples et LLM | Élevé : saturation, arrêt, mesures faussées | Plafonds mémoire, lancer les traitements par séquence ; modèle local modeste après arrêt de l'entraînement ; mesurer RSS/CPU/disque |
| Moteur Docker indisponible | Bloquant pour les essais d'infrastructure | Vérifier/redémarrer Docker Desktop après validation ; confirmer accès effectif au socket |
| PaySim absent, conditions inconnues | Bloquant pour entraîner/évaluer sur ce dataset | Acquérir, relever licence/version/SHA-256, contrôler schéma ; simulation autorisée seulement comme repli explicite |
| Versions et images ZooKeeper anciennes | Élevé : compatibilité, vulnérabilités, disponibilité registre | Vérifier versions, licences, scans et connecteurs ; documenter alternative et demander arbitrage si incompatibilité avec sécurité |
| Un hôte unique | Élevé : C1.4 partiellement couvert | Prouver pannes de processus, réplication et bascule ; pour perte hôte et HA intégrale, environnement multi-hôte à identifier sans dépense non autorisée |
| Déséquilibre et fuite de cible | Élevé : résultats trompeurs | Découpage temporel, features connues au scoring, transformations ajustées sur train ; PR-AUC et faux positifs en complément |
| Graphe trop grand ou PaySim peu cyclique | Moyen/élevé : Gephi inutilisable, interprétation abusive | Export borné et paramètres tracés ; aucun hub n'est preuve de blanchiment ; cas de test synthétique distinct si nécessaire |
| Duplications entre sinks | Élevé : agrégats/alertes incohérents | HDFS canonique, clés stables, upsert idempotent, reprise et rapprochement comptable testés |
| LLM halluciné ou indisponible | Élevé : motif incorrect, risque communication | Contexte factuel borné, validation structurée, pas d'accusation ni d'envoi ; erreur explicite et nouvel essai, sans faux résultat LLM |
| Plusieurs sources seulement nominales | Moyen : couverture RNCP discutée | Vraies décisions manuelles historisées comme seconde source ; confirmer avec l'enseignant avant revendication de couverture |
| Accès registres/paquets, Gephi ou modèle absent | Moyen : installation non reproductible | Vérifier disponibilité, licences, tailles et digests au premier jalon ; conserver procédure d'acquisition |

Aucun délai de remise, budget, identité de binôme, ressource externe ou accord enseignant n'est connu. Le plan donne une charge indicative, pas une promesse de calendrier. Les clarifications pédagogiques n'empêchent pas le cadrage ; elles conditionnent les preuves finales concernées.
