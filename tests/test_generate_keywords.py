
import csv
import os
import tempfile
import unittest

# This import will fail until the file is created in Phase 3
from src.pkm_linker.generate_keywords import generate_keyword_mappings

class TestGenerateKeywords(unittest.TestCase):

    def test_keyword_mapping_generation(self):
        # 1. Setup: Create a temporary directory and mock term file
        with tempfile.TemporaryDirectory() as tmpdir:
            term_file_path = os.path.join(tmpdir, "test_terms.md")
            csv_output_path = os.path.join(tmpdir, "keyword-mapping.csv")

            mock_terms = [
                "Cognitive Load Theory (CLT)",
                "Massachusetts Institute of Technology (MIT)",
                "MIT", # Deliberate duplicate to test conflict resolution
                "robotics" # A simple term with no alias
            ]

            with open(term_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(mock_terms))

            # 2. Action: Run the keyword generation function
            generate_keyword_mappings(term_file_path, csv_output_path)

            # 3. Assertion: Check if the CSV is created and has the correct content
            self.assertTrue(os.path.exists(csv_output_path))

            with open(csv_output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Create a dictionary for easy lookup from the generated CSV
            # { Alias: LinkTarget }
            generated_mappings = {row['Alias']: row['LinkTarget'] for row in rows}

            # --- Assertions for "Cognitive Load Theory (CLT)" ---
            expected_target_clt = "Cognitive Load Theory (CLT)"
            self.assertEqual(generated_mappings["Cognitive Load Theory (CLT)"], expected_target_clt)
            self.assertEqual(generated_mappings["Cognitive Load Theory"], expected_target_clt)
            self.assertEqual(generated_mappings["CLT"], expected_target_clt)

            # --- Assertions for "Massachusetts Institute of Technology (MIT)" ---
            # This also tests that the more descriptive target wins the conflict for the "MIT" alias
            expected_target_mit = "Massachusetts Institute of Technology (MIT)"
            self.assertEqual(generated_mappings["Massachusetts Institute of Technology (MIT)"], expected_target_mit)
            self.assertEqual(generated_mappings["Massachusetts Institute of Technology"], expected_target_mit)
            self.assertEqual(generated_mappings["MIT"], expected_target_mit)

            # --- Assertion for the simple term ---
            self.assertEqual(generated_mappings["robotics"], "robotics")
            
            # --- Assertion for total number of mappings ---
            # 3 for CLT, 3 for MIT, 1 for robotics = 7 total
            self.assertEqual(len(generated_mappings), 7)

if __name__ == '__main__':
    unittest.main()
