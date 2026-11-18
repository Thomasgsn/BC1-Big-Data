"""API BC1 : accès contrôlé aux résultats et décisions d'investigation."""

from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
import time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from bson import Decimal128, ObjectId
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from rncp_bc1.genai import generate, GenerationError

app = FastAPI(title="BC1 — Investigation de transactions synthétiques", version="0.1.0",
              description="Lecteur : consultation. Analyste : dossiers, décisions et brouillons. Quota général : 60 requêtes/minute/identité ; génération : 5/minute. Les scores ne prouvent pas une fraude.")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "api", "testserver"])
bearer = HTTPBearer(auto_error=False)
TransactionId = Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")]


def connect_sql():
    return psycopg.connect(host="postgres", dbname="bc1", user="bc1app", password=os.environ["POSTGRES_APP_PASSWORD"],
                           connect_timeout=3, options="-c statement_timeout=5000", row_factory=dict_row)


@lru_cache
def mongo():
    return MongoClient(host="mongo", port=27017, username="bc1app", password=os.environ["MONGO_APP_PASSWORD"],
                       authSource="fraud", serverSelectionTimeoutMS=3000, connectTimeoutMS=3000,
                       maxPoolSize=10, tz_aware=True)["fraud"]


def serializable(value):
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    if isinstance(value, Decimal128):
        return str(value.to_decimal())
    if isinstance(value, (UUID, ObjectId)):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@app.exception_handler(psycopg.Error)
@app.exception_handler(PyMongoError)
async def storage_error(request: Request, error):
    print(json.dumps({"event": "storage_unavailable", "error_type": type(error).__name__}), flush=True)
    return JSONResponse(status_code=503, content={"detail": "Stockage temporairement indisponible."})


@app.middleware("http")
async def request_log(request: Request, call_next):
    started = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Ni jeton, ni paramètres de requête, ni corps de décision dans les journaux.
        print(json.dumps({"event": "http_request", "method": request.method, "path": request.url.path[:256],
                          "status": status, "duration_ms": round((time.monotonic()-started)*1000, 2)}), flush=True)


def quota(principal_id: str, action="general", limit=60):
    with connect_sql() as conn:
        used = conn.execute("""INSERT INTO api_quota (principal_id, action, minute, used)
          VALUES (%s, %s, date_trunc('minute', now()), 1)
          ON CONFLICT (principal_id, action, minute) DO UPDATE SET used = api_quota.used + 1 RETURNING used""",
                            (principal_id, action)).fetchone()["used"]
    if used > limit:
        raise HTTPException(429, "Quota dépassé ; réessayer à la minute suivante.", headers={"Retry-After": str(60-int(time.time())%60)})


def user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None or credentials.scheme.lower() != "bearer" or not 32 <= len(credentials.credentials) <= 256:
        raise HTTPException(401, "Jeton Bearer requis.", headers={"WWW-Authenticate": "Bearer"})
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    with connect_sql() as conn:
        principal = conn.execute("SELECT principal_id, role FROM api_principal WHERE token_hash = %s AND active", (digest,)).fetchone()
    if principal is None:
        raise HTTPException(401, "Jeton invalide ou révoqué.", headers={"WWW-Authenticate": "Bearer"})
    quota(principal["principal_id"])
    return principal


def analyst(principal: dict = Depends(user)):
    if principal["role"] != "analyst":
        raise HTTPException(403, "Rôle analyste requis.")
    return principal


def alert_by_id(identifier):
    found = mongo().fraud_scores.find_one({"transaction_id": identifier, "is_alert": True}, sort=[("scored_at", DESCENDING)])
    if found is None:
        raise HTTPException(404, "Alerte introuvable.")
    return found


@app.get("/health/live", summary="Vérifier que le processus répond")
def live():
    return {"status": "alive"}


@app.get("/health/ready", summary="Vérifier les stockages, sans exiger un LLM chargé")
def ready():
    with connect_sql() as conn:
        conn.execute("SELECT 1")
    mongo().command("ping")
    return {"status": "ready"}


@app.get("/v1/alerts", summary="Lister les alertes modèle paginées")
def alerts(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), principal: dict = Depends(user)):
    cursor = mongo().fraud_scores.find({"is_alert": True}).sort("scored_at", DESCENDING).skip(offset).limit(limit)
    return {"items": serializable(list(cursor)), "limit": limit, "offset": offset, "synthetic_data": True}


@app.get("/v1/alerts/{transaction_id}", summary="Consulter les faits d'une alerte, sans conclure à une fraude certaine")
def alert(transaction_id: TransactionId, principal: dict = Depends(user)):
    return serializable(alert_by_id(transaction_id))


@app.get("/v1/metrics", summary="Consulter des agrégats bornés du Data Lab")
def metrics(limit: int = Query(50, ge=1, le=100), principal: dict = Depends(user)):
    return {"items": serializable(list(mongo().transaction_metrics.find().limit(limit))),
            "monetary_unit": "Unité monétaire locale PaySim, non précisée ; ne pas assimiler à EUR."}


@app.get("/v1/graph/exports", summary="Lister les snapshots de graphe complets")
def graph_exports(principal: dict = Depends(user)):
    return {"items": serializable(list(mongo().graph_snapshots.find({"status": "complete"}).limit(100)))}


@app.post("/v1/alerts/{transaction_id}/cases", summary="Ouvrir ou retrouver un dossier d'investigation")
def open_case(transaction_id: TransactionId, principal: dict = Depends(analyst)):
    alert_by_id(transaction_id)
    with connect_sql() as conn:
        case = conn.execute("""INSERT INTO investigation_case (case_id, transaction_id) VALUES (%s,%s)
          ON CONFLICT (transaction_id) DO UPDATE SET transaction_id=EXCLUDED.transaction_id RETURNING *""",
                            (uuid4(), transaction_id)).fetchone()
        conn.execute("INSERT INTO audit_event(principal_id, action, resource_id) VALUES (%s,'case_opened',%s)",
                     (principal["principal_id"], str(case["case_id"])))
    return serializable(case)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["suspicious", "legitimate", "uncertain"]
    reason: str = Field(min_length=1, max_length=2000, strict=True)
    origin: Literal["user_review", "automated_test"] = "user_review"

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


@app.post("/v1/cases/{case_id}/decisions", status_code=201, summary="Consigner une revue analyste avec clé d'idempotence UUID")
def decide(case_id: UUID, body: Decision, response: Response, idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
           principal: dict = Depends(analyst)):
    canonical = {"case_id": str(case_id), "principal_id": principal["principal_id"], **body.model_dump()}
    request_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with connect_sql() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (str(idempotency_key),))
        previous = conn.execute("SELECT * FROM analyst_decision WHERE idempotency_key=%s", (idempotency_key,)).fetchone()
        if previous:
            if previous["request_hash"] != request_hash:
                raise HTTPException(409, "Clé d'idempotence déjà utilisée avec un autre contenu.")
            response.status_code = 200
            previous.pop("request_hash")
            return serializable(previous)
        case = conn.execute("SELECT * FROM investigation_case WHERE case_id=%s FOR UPDATE", (case_id,)).fetchone()
        if case is None:
            raise HTTPException(404, "Dossier introuvable.")
        if case["status"] == "closed":
            raise HTTPException(409, "Dossier fermé.")
        version = conn.execute("SELECT coalesce(max(version),0)+1 AS next FROM analyst_decision WHERE case_id=%s", (case_id,)).fetchone()["next"]
        decision = conn.execute("""INSERT INTO analyst_decision
          (decision_id,case_id,analyst_id,outcome,reason,version,idempotency_key,request_hash,origin)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
          (uuid4(), case_id, principal["principal_id"], body.outcome, body.reason, version, idempotency_key, request_hash, body.origin)).fetchone()
        conn.execute("UPDATE investigation_case SET status='reviewed' WHERE case_id=%s", (case_id,))
        conn.execute("INSERT INTO audit_event(principal_id,action,resource_id) VALUES (%s,'decision_recorded',%s)",
                     (principal["principal_id"], str(decision["decision_id"])))
    decision.pop("request_hash")
    return serializable(decision)


@app.post("/v1/alerts/{transaction_id}/explanations", summary="Générer un brouillon local, jamais envoyer un message")
def explain(transaction_id: TransactionId, principal: dict = Depends(analyst)):
    quota(principal["principal_id"], "generate", 5)
    facts = serializable(alert_by_id(transaction_id))
    try:
        result = generate(facts, os.environ.get("LLM_BASE_URL", "http://ollama:11434"),
                          os.environ.get("LLM_MODEL", "qwen2.5:1.5b"))
    except GenerationError as error:
        print(json.dumps({"event": "draft_rejected", "reason": str(error)}), flush=True)
        if getattr(error, "generated_output", None) is not None:
            mongo().generation_attempts.insert_one({"_id": str(uuid4()), "status": "rejected",
              "transaction_id": transaction_id, "created_at": datetime.now(timezone.utc),
              "reason": str(error), "output": error.generated_output, "context": error.generation_context})
        raise HTTPException(503, "Génération locale indisponible ou sortie rejetée ; aucun message envoyé.") from None
    result["_id"] = str(uuid4())
    mongo().generated_explanations.insert_one(result)
    with connect_sql() as conn:
        conn.execute("INSERT INTO audit_event(principal_id,action,resource_id) VALUES (%s,'draft_generated',%s)",
                     (principal["principal_id"], transaction_id))
    return serializable(result)
