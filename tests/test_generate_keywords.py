
import csv
import json
import os
import tempfile
import unittest
from typing import Set

# This import will fail until the file is created in Phase 3
from src.pkm_linker.generate_keywords import generate_keyword_mappings

class TestGenerateKeywords(unittest.TestCase):

    def test_keyword_mapping_generation(self):
        # 1. Setup: Create a temporary directory and mock term file
        with tempfile.TemporaryDirectory() as tmpdir:
            term_file_path = os.path.join(tmpdir, "test_terms.md")
            unambiguous_csv = os.path.join(tmpdir, "unambiguous-keywords.csv")
            ambiguous_json = os.path.join(tmpdir, "ambiguous-keywords.json")

            mock_terms = [
                "Cognitive Load Theory (CLT)",
                "Massachusetts Institute of Technology (MIT)",
                "MIT", # Deliberate duplicate to test conflict resolution
                "robotics" # A simple term with no alias
            ]

            with open(term_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(mock_terms))

            # 2. Action: Run the keyword generation function
            generate_keyword_mappings(term_file_path, unambiguous_csv, ambiguous_json)

            # 3. Assertion: Check if the CSV is created and has the correct content
            self.assertTrue(os.path.exists(unambiguous_csv))
            self.assertTrue(os.path.exists(ambiguous_json))

            with open(unambiguous_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            rows_by_alias = {row['Alias']: row for row in rows}

            def clusters_for(alias: str) -> Set[str]:
                raw = rows_by_alias[alias]['Clusters']
                return {cluster.strip() for cluster in raw.split(';') if cluster.strip()}

            generated_mappings = {alias: row['LinkTarget'] for alias, row in rows_by_alias.items()}

            # --- Assertions for "Cognitive Load Theory (CLT)" ---
            expected_target_clt = "Cognitive Load Theory (CLT)"
            self.assertEqual(generated_mappings["Cognitive Load Theory (CLT)"], expected_target_clt)
            self.assertEqual(generated_mappings["Cognitive Load Theory"], expected_target_clt)
            self.assertEqual(generated_mappings["CLT"], expected_target_clt)
            self.assertIn("education-learning", clusters_for("Cognitive Load Theory (CLT)"))

            # --- Assertions for "Massachusetts Institute of Technology (MIT)" ---
            expected_target_mit = "Massachusetts Institute of Technology (MIT)"
            self.assertEqual(generated_mappings["Massachusetts Institute of Technology (MIT)"], expected_target_mit)
            self.assertEqual(generated_mappings["Massachusetts Institute of Technology"], expected_target_mit)
            # Alias "MIT" is ambiguous and should no longer appear in the unambiguous CSV
            self.assertNotIn("MIT", generated_mappings)
            self.assertTrue({"technology-computing", "organizations-institutions"} & clusters_for("Massachusetts Institute of Technology (MIT)"))

            # --- Assertion for the simple term ---
            self.assertEqual(generated_mappings["robotics"], "robotics")
            self.assertIn("technology-computing", clusters_for("robotics"))
            
            # --- Assertion for total number of mappings ---
            # 3 for CLT, 2 for MIT (without the ambiguous alias), 1 for robotics = 6 total
            self.assertEqual(len(generated_mappings), 6)

            # --- Ambiguous JSON assertions ---
            with open(ambiguous_json, 'r', encoding='utf-8') as f:
                ambiguous_entries = json.load(f)

            ambiguous_lookup = {entry["alias"]: entry for entry in ambiguous_entries}
            self.assertIn("MIT", ambiguous_lookup)
            self.assertEqual(
                set(ambiguous_lookup["MIT"]["candidates"]),
                {"MIT", "Massachusetts Institute of Technology (MIT)"},
            )
            self.assertEqual(
                set(ambiguous_lookup["MIT"]["source_terms"]),
                {"MIT", "Massachusetts Institute of Technology (MIT)"},
            )
            self.assertIn("technology-computing", ambiguous_lookup["MIT"]["clusters"])

if __name__ == '__main__':
    unittest.main()
