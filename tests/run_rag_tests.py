"""
Script automatisé pour tester le système RAG avec les questions définies.
Lance les tests, enregistre les résultats et génère un rapport d'analyse.
"""
import json
import requests
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Force UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
GATEWAY_URL = "http://localhost:8090"
TEST_QUESTIONS_PATH = Path(__file__).parent / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

class RAGTester:
    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url
        self.results = []
        
    def test_question(self, question: str, question_id: str = None) -> Dict[str, Any]:
        """Teste une question via l'API RAG"""
        print(f"  Testing: {question[:60]}...")
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.gateway_url}/rag/query",
                json={"question": question, "use_rag": True},
                timeout=60
            )
            response.raise_for_status()
            elapsed = time.time() - start_time
            
            data = response.json()
            
            result = {
                "question_id": question_id,
                "question": question,
                "answer": data.get("answer", ""),
                "sources": data.get("citations", []),  # Gateway returns 'citations' not 'sources'
                "chunks": data.get("chunks", []),
                "response_time": round(elapsed, 2),
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"    ✓ Response in {elapsed:.2f}s ({len(result['sources'])} sources)")
            return result
            
        except requests.exceptions.Timeout:
            print(f"    ✗ Timeout after 60s")
            return {
                "question_id": question_id,
                "question": question,
                "status": "timeout",
                "error": "Request timeout",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"    ✗ Error: {str(e)}")
            return {
                "question_id": question_id,
                "question": question,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Teste un scénario conversationnel"""
        print(f"\n🎬 Scenario: {scenario['name']}")
        print(f"   {scenario['description']}")
        
        scenario_results = {
            "scenario_id": scenario["scenario_id"],
            "name": scenario["name"],
            "description": scenario["description"],
            "turns": []
        }
        
        for turn in scenario["turns"]:
            turn_num = turn["turn"]
            question = turn["question"]
            
            print(f"\n  Turn {turn_num}:")
            result = self.test_question(question, f"{scenario['scenario_id']}_T{turn_num}")
            result["turn"] = turn_num
            result["expected_type"] = turn.get("expected_type")
            result["context_needed"] = turn.get("context_needed", False)
            result["notes"] = turn.get("notes", "")
            
            scenario_results["turns"].append(result)
            
            # Pause entre les questions pour simuler une vraie conversation
            time.sleep(1)
        
        return scenario_results
    
    def run_all_tests(self):
        """Lance tous les tests définis dans test_questions.json"""
        print("=" * 80)
        print("🧪 RAG TESTING SUITE")
        print("=" * 80)
        
        # Charger les questions
        with open(TEST_QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        test_suite = test_data["test_suite"]
        
        print(f"\n📋 Test Suite: {test_suite['name']}")
        print(f"📅 Date: {test_suite['date']}")
        print(f"📁 Documents: {', '.join(test_suite['documents'])}")
        
        # Test des questions individuelles
        print(f"\n{'=' * 80}")
        print("📝 INDIVIDUAL QUESTIONS")
        print(f"{'=' * 80}")
        
        individual_results = []
        for q in test_suite["questions"]:
            print(f"\n[Q{q['id']}] Category: {q['category']} | Difficulty: {q['difficulty']}")
            result = self.test_question(q["question"], f"Q{q['id']}")
            result.update({
                "category": q["category"],
                "difficulty": q["difficulty"],
                "expected_type": q["expected_type"],
                "expected_sources": q.get("expected_sources", []),
                "notes": q.get("notes", "")
            })
            individual_results.append(result)
            time.sleep(0.5)
        
        # Test des scénarios conversationnels
        print(f"\n{'=' * 80}")
        print("💬 CONVERSATIONAL SCENARIOS")
        print(f"{'=' * 80}")
        
        scenario_results = []
        for scenario in test_suite.get("conversational_scenarios", []):
            result = self.test_scenario(scenario)
            scenario_results.append(result)
        
        # Sauvegarder les résultats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = RESULTS_DIR / f"test_results_{timestamp}.json"
        
        full_results = {
            "test_info": {
                "suite_name": test_suite["name"],
                "run_date": datetime.now().isoformat(),
                "gateway_url": self.gateway_url
            },
            "individual_questions": individual_results,
            "conversational_scenarios": scenario_results,
            "summary": self.generate_summary(individual_results, scenario_results)
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(full_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'=' * 80}")
        print(f"✅ Results saved to: {results_file}")
        print(f"{'=' * 80}")
        
        # Afficher le résumé
        self.print_summary(full_results["summary"])
        
        return full_results
    
    def generate_summary(self, individual: List[Dict], scenarios: List[Dict]) -> Dict[str, Any]:
        """Génère un résumé des résultats"""
        total_questions = len(individual)
        total_scenarios = len(scenarios)
        total_turns = sum(len(s["turns"]) for s in scenarios)
        
        success_individual = sum(1 for r in individual if r["status"] == "success")
        success_turns = sum(
            sum(1 for t in s["turns"] if t["status"] == "success")
            for s in scenarios
        )
        
        avg_response_time_individual = sum(
            r.get("response_time", 0) for r in individual if r["status"] == "success"
        ) / max(success_individual, 1)
        
        all_turns = [t for s in scenarios for t in s["turns"]]
        avg_response_time_scenarios = sum(
            t.get("response_time", 0) for t in all_turns if t["status"] == "success"
        ) / max(success_turns, 1)
        
        return {
            "total_individual_questions": total_questions,
            "successful_individual": success_individual,
            "failed_individual": total_questions - success_individual,
            "success_rate_individual": round(success_individual / total_questions * 100, 1),
            "avg_response_time_individual": round(avg_response_time_individual, 2),
            
            "total_scenarios": total_scenarios,
            "total_turns": total_turns,
            "successful_turns": success_turns,
            "failed_turns": total_turns - success_turns,
            "success_rate_scenarios": round(success_turns / total_turns * 100, 1),
            "avg_response_time_scenarios": round(avg_response_time_scenarios, 2),
            
            "overall_success_rate": round(
                (success_individual + success_turns) / (total_questions + total_turns) * 100, 1
            )
        }
    
    def print_summary(self, summary: Dict[str, Any]):
        """Affiche le résumé des tests"""
        print(f"\n{'=' * 80}")
        print("📊 TEST SUMMARY")
        print(f"{'=' * 80}")
        
        print(f"\n📝 Individual Questions:")
        print(f"   Total: {summary['total_individual_questions']}")
        print(f"   ✓ Success: {summary['successful_individual']} ({summary['success_rate_individual']}%)")
        print(f"   ✗ Failed: {summary['failed_individual']}")
        print(f"   ⏱️  Avg Response Time: {summary['avg_response_time_individual']}s")
        
        print(f"\n💬 Conversational Scenarios:")
        print(f"   Total Scenarios: {summary['total_scenarios']}")
        print(f"   Total Turns: {summary['total_turns']}")
        print(f"   ✓ Success: {summary['successful_turns']} ({summary['success_rate_scenarios']}%)")
        print(f"   ✗ Failed: {summary['failed_turns']}")
        print(f"   ⏱️  Avg Response Time: {summary['avg_response_time_scenarios']}s")
        
        print(f"\n🎯 Overall Success Rate: {summary['overall_success_rate']}%")
        print(f"{'=' * 80}\n")


def main():
    """Point d'entrée principal"""
    tester = RAGTester(GATEWAY_URL)
    
    try:
        results = tester.run_all_tests()
        print("\n✅ Testing completed successfully!")
        return 0
    except FileNotFoundError:
        print(f"❌ Error: Test questions file not found at {TEST_QUESTIONS_PATH}")
        return 1
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Cannot connect to Gateway at {GATEWAY_URL}")
        print("   Make sure the Gateway service is running.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
