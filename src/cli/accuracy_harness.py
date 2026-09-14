import json, os, sys
from collections import defaultdict
from src.cli.multi_extractor import MultiLanguageExtractor

def calculate_metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def run_harness(ground_truth_file):
    with open(ground_truth_file, "r") as f:
        corpus = json.load(f)

    if len(corpus) < 50:
        print(f"WARNING: Corpus size is {len(corpus)}. Section 3 requires at least 50 repos.")

    tp, fp, fn = 0, 0, 0
    fp_logs, fn_logs = [], []

    for entry in corpus:
        repo_path = entry["repo"]
        lang = entry["language"]
        expected = {(e["file"], e["line"]): e["endpoint"] for e in entry["expected_findings"]}
        
        extractor = MultiLanguageExtractor(lang)
        actual_calls = []
        # Simplified recursive scan for harness
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(f".{lang}"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "rb") as bf:
                        calls = extractor.scan_code(bf.read(), filepath)
                        actual_calls.extend(calls)

        actual_map = {(c.file, c.line): c.resolved_endpoint for c in actual_calls}
        
        for key, ep in actual_map.items():
            if key in expected and expected[key] == ep:
                tp += 1
            else:
                fp += 1
                fp_logs.append(f"FP in {key[0]}:{key[1]} - Found {ep} but not in ground truth (Reason: Over-extraction or missing label)")
                
        for key, ep in expected.items():
            if key not in actual_map or actual_map[key] != ep:
                fn += 1
                fn_logs.append(f"FN in {key[0]}:{key[1]} - Expected {ep} but scanner missed it (Reason: Unresolved wrapper / dynamic method name)")

    p, r, f1 = calculate_metrics(tp, fp, fn)
    print("\n=== ACCURACY MEASUREMENT HARNESS ===")
    print(f"Total Repos Scanned: {len(corpus)}")
    print(f"Precision: {p:.4f} | Recall: {r:.4f} | F1: {f1:.4f}")
    print("\n--- False Positives ---")
    for log in fp_logs[:5]: print(log)
    print("\n--- False Negatives ---")
    for log in fn_logs[:5]: print(log)
    
    with open("README.md", "a") as rm:
        rm.write(f"\n## Scanner Accuracy\n- Precision: {p:.4f}\n- Recall: {r:.4f}\n- F1: {f1:.4f}\n")

if __name__ == "__main__":
    run_harness(sys.argv[1])
