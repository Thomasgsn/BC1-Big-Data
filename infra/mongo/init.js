// Exécuté seulement par l'image MongoDB sur un volume neuf.
const password = process.env.MONGO_APP_PASSWORD;
if (!password) throw new Error("MONGO_APP_PASSWORD requis");
const fraud = db.getSiblingDB("fraud");
fraud.createUser({user: "bc1app", pwd: password, roles: [{role: "readWrite", db: "fraud"}]});
for (const name of ["transaction_metrics", "graph_nodes", "graph_edges", "fraud_scores", "generated_explanations"]) {
  fraud.createCollection(name);
}
fraud.fraud_scores.createIndex({transaction_id: 1, model_version: 1}, {unique: true});
fraud.fraud_scores.createIndex({is_alert: 1, scored_at: -1});
fraud.graph_edges.createIndex({source: 1, target: 1});
fraud.generated_explanations.createIndex({transaction_id: 1, created_at: -1});
