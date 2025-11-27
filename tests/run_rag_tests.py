import sys
import io
from tests.test_rag_quality import run_all_tests

# Capture stdout
old_stdout = sys.stdout
sys.stdout = buffer = io.StringIO()

# Run tests
results = run_all_tests()

# Get output
output = buffer.getvalue()
sys.stdout = old_stdout

# Print to console
print(output)

# Save to file
with open("test_results_detailed.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("\n✅ Résultats sauvegardés dans test_results_detailed.txt")
