"""Mini-graphe artificiel de contrôle ; aucune capture ou analyse Gephi simulée."""

import csv
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from rncp_bc1.graph_export import export_graph


class GraphExportTest(unittest.TestCase):
    def setUp(self):
        self.document = {"snapshot_id": "synthetic-unit-test", "nodes": [{"node_id": "C1"}, {"node_id": "C2"}],
                         "edges": [{"edge_id": "a"*64, "source": "C1", "target": "C2", "transaction_count": 2, "total_amount": "0.30"}]}
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.destination = Path(self.temporary.name)/"export"

    def test_writes_directed_graph_and_exact_amounts(self):
        report = export_graph(self.document, self.destination)
        self.assertEqual(report["nodes"], 2)
        with (self.destination/"edges.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["TotalAmount"], "0.30")
        self.assertEqual(rows[0]["Type"], "Directed")
        self.assertEqual(rows[0]["Weight"], "2")
        with self.assertRaises(FileExistsError):
            export_graph(self.document, self.destination)

    def test_refuses_orphan_edges_without_publishing_output(self):
        self.document["edges"][0]["target"] = "C999"
        with self.assertRaises(ValueError):
            export_graph(self.document, self.destination)
        self.assertFalse(self.destination.exists())

    def test_refuses_duplicate_ids_and_unsafe_labels(self):
        for node in [{"node_id": "C1"}, {"node_id": "=HYPERLINK()"}]:
            doc = deepcopy(self.document)
            doc["nodes"].append(node)
            with self.subTest(node=node), self.assertRaises(ValueError):
                export_graph(doc, self.destination)

    def test_refuses_invalid_amount_and_count(self):
        for change in [{"total_amount": "NaN"}, {"total_amount": "-1"}, {"transaction_count": 0}, {"transaction_count": True}]:
            doc = deepcopy(self.document)
            doc["edges"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                export_graph(doc, self.destination)


if __name__ == "__main__":
    unittest.main()
