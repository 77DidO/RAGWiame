"""
Analyse automatique de la pertinence des réponses RAG.
Génère un rapport HTML avec les résultats sans interaction manuelle.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

RESULTS_DIR = Path(__file__).parent / "results"
ANALYSIS_DIR = Path(__file__).parent / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)


def auto_score_response(q):
    """Score automatique d'une réponse"""
    # Gérer les cas d'erreur où 'answer' est manquant
    if "answer" not in q:
        return {"exactitude": 0, "completude": 0, "concision": 0, "citations": 0, "pertinence": 0, "global": 0, "comment": "Erreur technique - Pas de réponse"}
    
    answer = q["answer"].lower()
    sources = q.get("sources", [])
    
    scores = {}
    
    # 1. Exactitude (basée sur présence de sources et refus appropriés)
    if "je n'ai pas trouvé" in answer or "aucune information" in answer:
        scores["exactitude"] = 5 if q.get("expected_type") == "refusal" else 2
    elif len(sources) > 0:
        scores["exactitude"] = 4
    else:
        scores["exactitude"] = 3
    
    # 2. Complétude (basée sur longueur)
    length = len(answer)
    if length < 50:
        scores["completude"] = 2
    elif length < 150:
        scores["completude"] = 3
    elif length < 300:
        scores["completude"] = 4
    else:
        scores["completude"] = 5
    
    # 3. Concision
    if length < 50:
        scores["concision"] = 2
    elif length > 500:
        scores["concision"] = 3
    else:
        scores["concision"] = 5
    
    # 4. Citations
    num_sources = len(sources)
    if num_sources == 0:
        scores["citations"] = 1
    elif num_sources == 1:
        scores["citations"] = 3
    elif num_sources <= 3:
        scores["citations"] = 5
    else:
        scores["citations"] = 4
    
    # 5. Pertinence (overlap mots-clés)
    question_words = set(q["question"].lower().split())
    answer_words = set(answer.split())
    overlap = len(question_words & answer_words)
    
    if overlap > 5:
        scores["pertinence"] = 5
    elif overlap > 3:
        scores["pertinence"] = 4
    elif overlap > 1:
        scores["pertinence"] = 3
    else:
        scores["pertinence"] = 2
    
    scores["global"] = round(sum(scores.values()) / len(scores), 1)
    
    # Commentaire heuristique par question
    comments = []
    if not sources:
        comments.append("Aucune citation fournie.")
    if "question :" in answer or "reponse :" in answer:
        comments.append("Bloc QA parasite detecte dans la reponse.")
    if q.get("expected_type") in {"amount", "financial_simple", "financial_complex"} and not any(ch.isdigit() for ch in answer):
        comments.append("Pas de montant explicite retourne.")
    if q.get("expected_type") == "refusal" and sources:
        comments.append("Devait refuser sans citer de sources.")
    if q.get("expected_type") == "refusal" and not ("pas trouve" in answer or "ne permet pas de repondre" in answer or "ne sont pas fournies" in answer):
        comments.append("Pas de refus explicite alors que question hors corpus.")
    scores["comment"] = " ".join(comments) if comments else ""
    
    return scores



def generate_diagnostic_html(results):
    """Génère un diagnostic dynamique basé sur les résultats"""
    issues = []
    
    # Analyser toutes les questions (individuelles + scénarios)
    all_questions = results.get("individual_questions", [])
    for scen in results.get("conversational_scenarios", []):
        all_questions.extend(scen.get("turns", []))
        
    total = len(all_questions)
    if total == 0:
        return "<p>Aucune donnée à analyser.</p>"
        
    # 1. Blocs QA parasites
    parasite_count = sum(1 for q in all_questions if "Question :" in q.get("answer", "") or "Reponse :" in q.get("answer", ""))
    if parasite_count > 0:
        issues.append(f"<li>⚠️ <strong>Blocs Q/A parasites</strong> : {parasite_count} réponses contiennent encore des hallucinations de format ({round(parasite_count/total*100)}%).</li>")
    else:
        issues.append("<li>✅ <strong>Format</strong> : Aucun bloc Q/A parasite détecté.</li>")
        
    # 2. Citations manquantes
    no_citations = sum(1 for q in all_questions if len(q.get("sources", [])) == 0 and q.get("expected_type") != "refusal")
    if no_citations > 0:
        issues.append(f"<li>⚠️ <strong>Citations manquantes</strong> : {no_citations} réponses n'ont aucune source alors qu'elles devraient.</li>")
    
    # 3. Refus échoués
    refusal_failed = sum(1 for q in all_questions if q.get("expected_type") == "refusal" and len(q.get("sources", [])) > 0)
    if refusal_failed > 0:
        issues.append(f"<li>🚫 <strong>Refus échoués</strong> : {refusal_failed} questions hors-corpus ont généré des citations (devraient être 0).</li>")
    else:
        issues.append("<li>✅ <strong>Refus</strong> : Les questions hors-corpus sont bien gérées (0 citations).</li>")
        
    # 4. Montants trouvés
    amount_questions = [q for q in all_questions if q.get("expected_type") in ("amount", "financial_simple", "financial_complex")]
    amount_issues = sum(1 for q in amount_questions if not any(c.isdigit() for c in q.get("answer", "")))
    if amount_issues > 0:
        issues.append(f"<li>💰 <strong>Montants manquants</strong> : {amount_issues} questions financières sans chiffre dans la réponse.</li>")

    html = "<ul>" + "".join(issues) + "</ul>"
    return html


def generate_html_report(results_file):
    """Génère un rapport HTML"""
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Analyser toutes les questions
    analyzed = []
    for q in results["individual_questions"]:
        if q["status"] != "success":
            continue
        
        scores = auto_score_response(q)
        analyzed.append({
            "id": q["question_id"],
            "category": q["category"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "answer": q["answer"],
            "sources": q.get("sources", []),
            "response_time": q.get("response_time", 0),
            "scores": scores
        })
    
    # Calculer moyennes
    if not analyzed:
        print("❌ Aucune question à analyser")
        return None
    
    avg_scores = {
        "exactitude": round(sum(q["scores"]["exactitude"] for q in analyzed) / len(analyzed), 2),
        "completude": round(sum(q["scores"]["completude"] for q in analyzed) / len(analyzed), 2),
        "concision": round(sum(q["scores"]["concision"] for q in analyzed) / len(analyzed), 2),
        "citations": round(sum(q["scores"]["citations"] for q in analyzed) / len(analyzed), 2),
        "pertinence": round(sum(q["scores"]["pertinence"] for q in analyzed) / len(analyzed), 2),
        "global": round(sum(q["scores"]["global"] for q in analyzed) / len(analyzed), 2)
    }
    
    # Générer HTML
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = ANALYSIS_DIR / f"report_{timestamp}.html"
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport d'Analyse RAG - {timestamp}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #FFD300; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric {{ background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #FFD300; }}
        .metric-label {{ font-size: 0.9em; color: #666; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .stars {{ color: #FFD300; }}
        .question {{ background: #fafafa; padding: 20px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #ddd; }}
        .question.excellent {{ border-left-color: #4CAF50; }}
        .question.good {{ border-left-color: #8BC34A; }}
        .question.average {{ border-left-color: #FFC107; }}
        .question.poor {{ border-left-color: #FF9800; }}
        .question.bad {{ border-left-color: #F44336; }}
        .q-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .q-id {{ font-weight: bold; color: #FFD300; }}
        .q-category {{ background: #e0e0e0; padding: 3px 8px; border-radius: 3px; font-size: 0.85em; }}
        .q-text {{ font-weight: bold; color: #333; margin: 10px 0; }}
        .answer {{ color: #555; margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }}
        .sources {{ font-size: 0.9em; color: #777; margin: 10px 0; }}
        .scores {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; margin-top: 10px; }}
        .score-item {{ text-align: center; padding: 8px; background: white; border-radius: 3px; }}
        .score-label {{ font-size: 0.8em; color: #666; }}
        .score-value {{ font-size: 1.3em; font-weight: bold; color: #FFD300; }}
        .commentary {{ background: #fffdf3; border: 1px solid #ffe58f; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .commentary h2 {{ margin-top: 0; color: #b58b00; }}
        .commentary ul, .commentary ol {{ margin: 10px 0 0 20px; }}
        .comment {{ font-size: 0.9em; color: #8b6b00; margin-top: 8px; }}
        .scenario {{ background: #f7f9ff; padding: 16px; border-radius: 6px; border-left: 4px solid #6fa8ff; margin: 20px 0; }}
        .turn {{ margin: 12px 0 0 10px; padding: 10px; background: #ffffff; border-radius: 4px; border: 1px solid #e6e9f2; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rapport d'Analyse RAG</h1>
        <p><strong>Date:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Fichier source:</strong> {results_file.name}</p>
        <p><strong>Questions analysées:</strong> {len(analyzed)}</p>
        
        <div class="commentary">
            <h2>🔎 Diagnostic Dynamique</h2>
            {generate_diagnostic_html(results)}
        </div>
        
        <h2>⭐ Scores Moyens</h2>
        <div class="summary">
            <div class="metric">
                <div class="metric-label">Exactitude</div>
                <div class="metric-value">{avg_scores['exactitude']}/5</div>
                <div class="stars">{'⭐' * int(avg_scores['exactitude'])}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Complétude</div>
                <div class="metric-value">{avg_scores['completude']}/5</div>
                <div class="stars">{'⭐' * int(avg_scores['completude'])}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Concision</div>
                <div class="metric-value">{avg_scores['concision']}/5</div>
                <div class="stars">{'⭐' * int(avg_scores['concision'])}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Citations</div>
                <div class="metric-value">{avg_scores['citations']}/5</div>
                <div class="stars">{'⭐' * int(avg_scores['citations'])}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Pertinence</div>
                <div class="metric-value">{avg_scores['pertinence']}/5</div>
                <div class="stars">{'⭐' * int(avg_scores['pertinence'])}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🎯 Global</div>
                <div class="metric-value">{avg_scores['global']}/5</div>
                <div class="stars">{'⭐' * int(avg_scores['global'])}</div>
            </div>
        </div>
        
        <h2>📝 Détail par Question</h2>
"""
    
    # Ajouter chaque question
    for q in analyzed:
        score_class = (
            "excellent" if q["scores"]["global"] >= 4.5 else
            "good" if q["scores"]["global"] >= 4.0 else
            "average" if q["scores"]["global"] >= 3.0 else
            "poor" if q["scores"]["global"] >= 2.0 else
            "bad"
        )
        
        comment_html = f"<div class='score-item'><div class='score-label'>Commentaire</div><div class='score-value' style='font-size:0.9em;'>{q['scores']['comment']}</div></div>" if q['scores'].get('comment') else ""
        
        html += f"""
        <div class="question {score_class}">
            <div class="q-header">
                <span class="q-id">{q['id']}</span>
                <span class="q-category">{q['category']} | {q['difficulty']}</span>
            </div>
            <div class="q-text">❓ {q['question']}</div>
            <div class="sources" style="background:#e3f2fd; color:#0d47a1; padding:8px; border-radius:4px; margin-bottom:5px; font-size:0.9em;">
                🎯 <strong>Attendu:</strong> Type=<code>{q.get('expected_type','N/A')}</code> 
                {f"| Note: <em>{q['notes']}</em>" if q.get('notes') else ""}
            </div>
            <div class="answer">💬 {q['answer'][:300]}{'...' if len(q['answer']) > 300 else ''}</div>
            <div class="sources">📚 {len(q['sources'])} source(s) | ⏱️ {q['response_time']}s</div>
            <div class="scores">
                <div class="score-item">
                    <div class="score-label">Exactitude</div>
                    <div class="score-value">{q['scores']['exactitude']}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Complétude</div>
                    <div class="score-value">{q['scores']['completude']}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Concision</div>
                    <div class="score-value">{q['scores']['concision']}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Citations</div>
                    <div class="score-value">{q['scores']['citations']}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Pertinence</div>
                    <div class="score-value">{q['scores']['pertinence']}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">🎯 Global</div>
                    <div class="score-value">{q['scores']['global']}</div>
                </div>
                {comment_html}
            </div>
        </div>
"""
    
    # Scénarios conversationnels
    scenarios = results.get("conversational_scenarios", [])
    if scenarios:
        html += "<h2>🗂️ Scénarios conversationnels</h2>"
        for scen in scenarios:
            html += f"<div class='scenario'><h3>🎬 {scen.get('name','')}</h3><p><em>{scen.get('description','')}</em></p>"
            for turn in scen.get("turns", []):
                t_scores = auto_score_response(turn)
                t_class = (
                    "excellent" if t_scores["global"] >= 4.5 else
                    "good" if t_scores["global"] >= 4.0 else
                    "average" if t_scores["global"] >= 3.0 else
                    "poor" if t_scores["global"] >= 2.0 else
                    "bad"
                )
                comment_html = f"<div class='comment'>Commentaire: {t_scores['comment']}</div>" if t_scores.get('comment') else ""
                
                html += f"""
                <div class="turn {t_class}">
                    <div><strong>Turn {turn.get('turn','')}</strong> | ⏱️ {turn.get('response_time',0)}s | 🔗 {len(turn.get('sources',[]))} source(s)</div>
                    <div><strong>Q:</strong> {turn.get('question','')}</div>
                    <div style="background:#e3f2fd; color:#0d47a1; padding:4px 8px; border-radius:4px; margin:4px 0; font-size:0.85em;">
                        🎯 <strong>Attendu:</strong> Type=<code>{turn.get('expected_type','N/A')}</code> {f"| {turn['notes']}" if turn.get('notes') else ""}
                    </div>
                    <div><strong>R:</strong> {turn.get('answer','')[:300]}{'...' if len(turn.get('answer',''))>300 else ''}</div>
                    <div class="scores" style="margin-top:8px;">
                        <div class="score-item"><div class="score-label">Exactitude</div><div class="score-value">{t_scores['exactitude']}</div></div>
                        <div class="score-item"><div class="score-label">Complétude</div><div class="score-value">{t_scores['completude']}</div></div>
                        <div class="score-item"><div class="score-label">Concision</div><div class="score-value">{t_scores['concision']}</div></div>
                        <div class="score-item"><div class="score-label">Citations</div><div class="score-value">{t_scores['citations']}</div></div>
                        <div class="score-item"><div class="score-label">Pertinence</div><div class="score-value">{t_scores['pertinence']}</div></div>
                        <div class="score-item"><div class="score-label">🎯 Global</div><div class="score-value">{t_scores['global']}</div></div>
                    </div>
                    {comment_html}
                </div>
                """
            html += "</div>"
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_file, avg_scores


def main():
    print("=" * 80)
    print("🔍 ANALYSE AUTOMATIQUE DE PERTINENCE")
    print("=" * 80)
    
    # Trouver le fichier le plus récent
    result_files = sorted(RESULTS_DIR.glob("test_results_*.json"), reverse=True)
    
    if not result_files:
        print("\n❌ Aucun fichier de résultats trouvé")
        return 1
    
    results_file = result_files[0]
    print(f"\n📂 Analyse de: {results_file.name}")
    
    html_file, avg_scores = generate_html_report(results_file)
    
    print(f"\n⭐ SCORES MOYENS:")
    print(f"   Exactitude:  {avg_scores['exactitude']}/5")
    print(f"   Complétude:  {avg_scores['completude']}/5")
    print(f"   Concision:   {avg_scores['concision']}/5")
    print(f"   Citations:   {avg_scores['citations']}/5")
    print(f"   Pertinence:  {avg_scores['pertinence']}/5")
    print(f"\n   🎯 GLOBAL:    {avg_scores['global']}/5")
    
    print(f"\n✅ Rapport HTML généré: {html_file}")
    print(f"\n💡 Ouvrez le fichier dans votre navigateur pour voir le rapport détaillé")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())
