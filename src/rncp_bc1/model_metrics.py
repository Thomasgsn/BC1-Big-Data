"""Métriques exactes de confusion ; aucune mesure de modèle simulée."""


def confusion_metrics(tp: int, fp: int, tn: int, fn: int) -> dict:
    if any(not isinstance(x, int) or isinstance(x, bool) or x < 0 for x in [tp, fp, tn, fn]):
        raise ValueError("Les effectifs doivent être des entiers positifs ou nuls.")
    if tp+fp+tn+fn == 0:
        raise ValueError("Jeu d'évaluation vide.")
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else None
    f1 = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0
    f2 = 5*tp/(5*tp+fp+4*fn) if 5*tp+fp+4*fn else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1, "f2": f2,
            "false_positive_rate": fp/(fp+tn) if fp+tn else None,
            "accuracy": (tp+tn)/(tp+fp+tn+fn)}


def select_threshold(candidates: list[dict]) -> dict:
    if not candidates or any(x["recall"] is None for x in candidates):
        raise ValueError("Des fraudes observées et des seuils évalués sont requis pour sélectionner un seuil.")
    # F2 favorise le rappel ; en cas d'égalité, préférer précision puis seuil plus élevé.
    return max(candidates, key=lambda x: (x["f2"], x["precision"], x["threshold"]))
