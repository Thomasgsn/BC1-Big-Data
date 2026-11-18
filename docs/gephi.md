# Gephi — analyse sur export Mongo réel

État : export Mongo réel et algorithmes Gephi Toolkit **0.11.4** exécutés. Les degrés ont été rapprochés indépendamment de toutes les arêtes CSV ; 1 597 nœuds et 1 000 arêtes GEXF vérifiés. Le [rapport réel](evidence/p5/report.json), les [degrés](evidence/p5/degrees.csv), le [rendu PNG](evidence/p5/largest-five-components.png) et le [manifeste](evidence/p5/manifest.json) sont conservés. Ce rendu provient du moteur Gephi, **ce rendu seul n'est pas une capture de l'interface desktop**, désormais disponible dans les preuves du client Linux.

Modularité pondérée sur projection non orientée : **0,995408**, résolution 1, aléa désactivé ; **597 communautés et 597 composantes faibles**. La formule indépendante `1 - somme((arêtes_composante / 1000)^2)` retrouve cette modularité car toutes les composantes sont déconnectées et leurs arêtes ont poids 1. La fragmentation explique le résultat ; aucune preuve de blanchiment. Degré entrant maximal : **23**, compte synthétique `C1590550415`, degré sortant 0. Les cinq plus grandes composantes ont 24, 18, 16, 15 et 15 nœuds.

Le rendu sélectionne seulement ces cinq composantes (88 nœuds, 83 arêtes), couleurs par communauté, taille par degré total, étiquettes des hubs uniquement. Disposition Yifan Hu 200 itérations, positions initiales seed 42, puis translation/échelle des composantes pour limiter le vide ; aucun changement topologique. Le GEXF complet est exporté avant ce filtre. Les deux premiers essais de PNG ont échoué (dépendance desktop puis codec Batik) ; la version finale utilise SVG Gephi puis Batik/ImageIO headless, réellement exécutée et inspectée.

```bash
docker compose run --rm gephi-toolkit
```

Cette commande refuse d'écraser un résultat existant. Pour un nouveau calcul, passer `compile exec:java -Dexec.mainClass=fr.rncp.bc1.NetworkAnalysis '-Dexec.args=/exports/gephi/SNAPSHOT /exports/analysis/NOUVELLE_VERSION' -Dexec.cleanupDaemonThreads=false`. Sources : [Toolkit officiel](https://gephi.org/toolkit/) et [statistique Modularity](https://github.com/gephi/gephi/blob/master/modules/StatisticsPlugin/src/main/java/org/gephi/statistics/plugin/Modularity.java). L'application Gephi desktop n'est pas installée au chemin standard ; procédure de capture à terminer :

1. Après ingestion vérifiée, publier une fenêtre avec `scripts/spark-job.sh publish_graph` puis exécuter `scripts/export-graph.sh` ; commandes détaillées dans [installation.md](installation.md).
2. Conserver `exports/gephi/<snapshot>/manifest.json` : provenance déclarée, snapshot, nœuds/arêtes, pondération et empreintes CSV.
3. Dans Gephi, créer un projet ; importer `nodes.csv` comme table des nœuds puis `edges.csv` comme table des arêtes. Choisir UTF-8, séparateur virgule et graphe orienté. Vérifier les correspondances `Id`, `Source`, `Target`, `Type`, `Weight` et les comptages avant analyse.
4. Exécuter les statistiques de degré puis modularité ; conserver la version Gephi, résolution, pondération, aléa/seed si disponible et toute option effectivement proposée. L'interface précise dépendra de la version installée et devra être vérifiée, sans inventer des boutons ou résultats.
5. Colorer les communautés et dimensionner les nœuds avec une métrique explicitement nommée ; choisir une disposition lisible et sauvegarder le projet Gephi.
6. Capturer les écrans réels avec paramètres, fenêtre et commentaire d'analyse. Relier les hubs aux données d'origine ; distinguer poids financier (`TotalAmount`) et fréquence des transactions (`Weight`).

L'export conserve le nombre de transactions comme poids. Un sous-graphe temporel modifie les degrés et communautés observés ; annoncer la fenêtre et les limites. Un compte marchand très connecté peut être normal. Ni un hub ni une communauté n'établit une fraude ou un blanchiment. PaySim n'apporte pas de vérité terrain « réseau de blanchiment » à inventer pour évaluer Gephi.

## Captures du logiciel client réellement obtenues

Le client Gephi Linux officiel 0.11.4 a ouvert `five-components.gephi` dans un écran X11 isolé (Xvfb/Openbox, sans port public). Captures inspectées : [aperçu](evidence/p5/gephi-desktop-preview.png) et [table des degrés/classes](evidence/p5/gephi-desktop-data-laboratory.png). Le [projet portable](evidence/p5/five-components.gephi) contient le sous-graphe déclaré de 88 nœuds/83 arêtes ; le GEXF complet reste distinct. Les classes numériques et couleurs peuvent changer d'une exécution à l'autre : leur numéro n'est pas une identité stable de communauté.

[Manifeste, source et empreintes](evidence/p5/desktop-manifest.json). L'installation native macOS a échoué au montage DMG ; l'extraction alternative a donné une signature invalide et n'a pas été exécutée. La voie Linux utilise une archive officielle vérifiée par SHA-256, aucun contournement de Gatekeeper ni modification de la sécurité macOS.

Commandes de la voie Linux : télécharger l'archive du manifeste dans `tmp/gephi-0.11.4-linux-x64.tar.gz`, générer un projet avec le Toolkit, puis `docker compose up -d gephi-desktop`. Le script `scripts/gephi-desktop.sh` ouvre ce fichier via le véritable client et enregistre les premières captures. Prévoir le téléchargement des bibliothèques système ; ce profil d'outillage est optionnel et son absence n'affecte pas la plateforme. `docker compose stop gephi-desktop` conserve les fichiers.
