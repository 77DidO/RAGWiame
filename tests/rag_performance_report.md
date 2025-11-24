# RAG Performance & Quality Report
Date: 2025-11-23 19:58:23

## Summary
- **Total Tests**: 20
- **Success Rate**: 6/20 (30.0%)
- **Average Latency**: 6.55s
- **Min Latency**: 0.03s
- **Max Latency**: 32.70s

## Detailed Results

| ID | Category | Question | Success | Latency | Keywords Found |
|----|----------|----------|---------|---------|----------------|
| 1 | Specific Price | Quel est le prix unitaire du TUBE TELECOM PVC LST D60 ? | ✅ | 15.05s | 1,53 |
| 2 | Specific Price | Quel est le prix du TUYAU ASSAINISSEMENT BETON ARME D1000 ? | ❌ | 4.20s | N/A |
| 3 | Labor Cost | Quel est le coût journalier d'un CHEF CHANTIER ? | ❌ | 4.19s | N/A |
| 4 | Labor Cost | Quel est le coût d'un MACON ? | ❌ | 4.29s | N/A |
| 5 | Material Price | Quel est le prix d'un sac de CIMENT COURANT 25KG ? | ❌ | 4.53s | N/A |
| 6 | Material Price | Combien coûte la GAINE TPC COURONNE ROUGE D75 ? | ❌ | 4.22s | N/A |
| 7 | Equipment Cost | Quel est le coût de la MINI PELLE 8/10T ? | ❌ | 7.10s | N/A |
| 8 | Equipment Cost | Quel est le coût de la PELLE 21T ? | ✅ | 6.34s | 800 |
| 9 | Specific Item | Quel est le prix de la TÊTE SÉCURITÉ Ø 500 COMPLÈTE ? | ❌ | 4.86s | N/A |
| 10 | Specific Item | Combien coûte un BURIN 350MM REAFFUTABLE ? | ❌ | 4.68s | N/A |
| 11 | Vague/Context | Donnez-moi les tarifs des tuyaux d'assainissement béton. | ❌ | 4.40s | N/A |
| 12 | Vague/Context | Quels sont les coûts des différents personnels de chantier ? | ✅ | 13.05s | Chef |
| 13 | Vague/Context | Quels sont les engins disponibles et leurs coûts ? | ✅ | 32.70s | Pelle, 352, 480 |
| 14 | Specific Detail | Quel est le code article pour le CIMENT FONDU SAC 25 KG ? | ❌ | 5.17s | N/A |
| 15 | Specific Detail | Quelle est la référence de la GAINE TPC COURONNE ROUGE D90 ? | ❌ | 3.92s | N/A |
| 16 | Comparison | Quel est le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE ? | ❌ | 5.02s | N/A |
| 17 | Comparison | Quel est le prix du TUYAU D1000 par rapport au D300 ? | ❌ | 2.87s | N/A |
| 18 | Company Info | De quoi parle le document WIAME VRD ? | ✅ | 0.03s | Présentation, entreprise |
| 19 | Supplier | Qui est le fournisseur pour les tubes télécom ? | ✅ | 3.09s | WIAME |
| 20 | Location | Où se trouve le traitement de déchets ultimes ? | ❌ | 1.35s | N/A |

## Failed Tests Analysis

### Test 2: Quel est le prix du TUYAU ASSAINISSEMENT BETON ARME D1000 ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['139.0', '139,0', '139']

### Test 3: Quel est le coût journalier d'un CHEF CHANTIER ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['332']

### Test 4: Quel est le coût d'un MACON ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['256']

### Test 5: Quel est le prix d'un sac de CIMENT COURANT 25KG ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['7.67', '7,67']

### Test 6: Combien coûte la GAINE TPC COURONNE ROUGE D75 ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['44.46', '44,46']

### Test 7: Quel est le coût de la MINI PELLE 8/10T ?
- **Error/Response**: 
Réponse : Le coût de la MINI PELLE 8/10T n'est pas spécifié dans les documents.
- **Missing Keywords**: ['352']

### Test 9: Quel est le prix de la TÊTE SÉCURITÉ Ø 500 COMPLÈTE ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['193.94', '193,94']

### Test 10: Combien coûte un BURIN 350MM REAFFUTABLE ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['7.20', '7,20']

### Test 11: Donnez-moi les tarifs des tuyaux d'assainissement béton.
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['139', '28.2', '38.2', '54.49', '70.73']

### Test 14: Quel est le code article pour le CIMENT FONDU SAC 25 KG ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['2104010203', '8341']

### Test 15: Quelle est la référence de la GAINE TPC COURONNE ROUGE D90 ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['D90', '56.18']

### Test 16: Quel est le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE ?
- **Error/Response**: 
Réponse : Selon les documents fournis, le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE est le CHEF CHANTIER, avec un coût de 308 € par jour [1]. Le coût du CHEF EQUIPE est de 256 € par jour [1].
- **Missing Keywords**: ['332', 'identique', 'même prix']

### Test 17: Quel est le prix du TUYAU D1000 par rapport au D300 ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['139', '28.2']

### Test 20: Où se trouve le traitement de déchets ultimes ?
- **Error/Response**: 
Réponse : Je n'ai pas trouvé l'information dans les documents.
- **Missing Keywords**: ['VERT LE GRAND']
