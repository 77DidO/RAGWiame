# RAG Performance & Quality Report
Date: 2025-11-25 23:29:06

## Summary
- **Total Tests**: 20
- **Success Rate**: 1/20 (5.0%)
- **Average Latency**: 11.02s
- **Min Latency**: 5.37s
- **Max Latency**: 21.48s

## Detailed Results

| ID | Category | Question | Success | Latency | Keywords Found |
|----|----------|----------|---------|---------|----------------|
| 1 | Specific Price | Quel est le prix unitaire du TUBE TELECOM PVC LST D60 ? | ❌ | 11.92s | N/A |
| 2 | Specific Price | Quel est le prix du TUYAU ASSAINISSEMENT BETON ARME D1000 ? | ❌ | 12.98s | N/A |
| 3 | Labor Cost | Quel est le coût journalier d'un CHEF CHANTIER ? | ❌ | 12.09s | N/A |
| 4 | Labor Cost | Quel est le coût d'un MACON ? | ❌ | 10.53s | N/A |
| 5 | Material Price | Quel est le prix d'un sac de CIMENT COURANT 25KG ? | ❌ | 8.65s | N/A |
| 6 | Material Price | Combien coûte la GAINE TPC COURONNE ROUGE D75 ? | ❌ | 13.70s | N/A |
| 7 | Equipment Cost | Quel est le coût de la MINI PELLE 8/10T ? | ❌ | 13.85s | N/A |
| 8 | Equipment Cost | Quel est le coût de la PELLE 21T ? | ❌ | 14.37s | N/A |
| 9 | Specific Item | Quel est le prix de la TETE SECURITE Ø 500 COMPLETE ? | ❌ | 9.19s | N/A |
| 10 | Specific Item | Combien coûte un BURIN 350MM REAFFUTABLE ? | ❌ | 13.46s | N/A |
| 11 | Vague/Context | Donnez-moi les tarifs des tuyaux d'assainissement béton. | ❌ | 13.10s | N/A |
| 12 | Vague/Context | Quels sont les coûts des différents personnels de chantier ? | ❌ | 9.55s | N/A |
| 13 | Vague/Context | Quels sont les engins disponibles et leurs coûts ? | ❌ | 8.56s | N/A |
| 14 | Specific Detail | Quel est le code article pour le CIMENT FONDU SAC 25 KG ? | ❌ | 7.83s | N/A |
| 15 | Specific Detail | Quelle est la référence de la GAINE TPC COURONNE ROUGE D90 ? | ✅ | 5.37s | D90 |
| 16 | Comparison | Quel est le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE ? | ❌ | 6.56s | N/A |
| 17 | Comparison | Quel est le prix du TUYAU D1000 par rapport au D300 ? | ❌ | 7.21s | N/A |
| 18 | Company Info (DOCX) | De quoi parle le document WIAME VRD ? | ❌ | 21.48s | N/A |
| 19 | Supplier (DOCX/Excel) | Qui est le fournisseur pour les tubes telecom ? | ❌ | 13.41s | N/A |
| 20 | Location (PDF/DOCX) | Où se trouve le traitement de déchets ultimes ? | ❌ | 6.51s | N/A |

## Failed Tests Analysis

### Test 1: Quel est le prix unitaire du TUBE TELECOM PVC LST D60 ?
- **Error/Response**: 
Réponse : Je suis désolé, mais le contexte fourni ne contient pas d'information pertinente sur le prix unitaire du TUBE TELECOM PVC LST D60.
- **Missing Keywords**: ['1.53', '1,53']

### Test 2: Quel est le prix du TUYAU ASSAINISSEMENT BETON ARME D1000 ?
- **Error/Response**: 
Réponse : Le contexte ne contient pas de données sur le prix du Tuyau Assainissement Beton Arme D1000. Il est donc impossible de fournir une réponse précise à cette question.
- **Missing Keywords**: ['139.0', '139,0', '139']

### Test 3: Quel est le coût journalier d'un CHEF CHANTIER ?
- **Error/Response**: 
Réponse : Le coût journalier d'un chef chantier n'est pas spécifié dans le contexte fourni. Cependant, il est possible de déduire que le coût journalier d'un chef chantier peut être influencé par plusieurs facteurs, tels que son niveau d'expérience, ses compétences, son emplacement géographique, etc. Il est donc impossible de fournir une réponse précise sans plus de détails sur le contexte.
- **Missing Keywords**: ['332']

### Test 4: Quel est le coût d'un MACON ?
- **Error/Response**: 
Réponse : Le document fourni ne contient pas de données spécifiques sur le coût d'un MACON. Il est possible que le coût soit inclus dans les données de calcul de prix, mais il n'y a pas de ligne spécifique pour le MACON dans les données fournies.
- **Missing Keywords**: ['256']

### Test 5: Quel est le prix d'un sac de CIMENT COURANT 25KG ?
- **Error/Response**: 
Réponse : Il n'y a pas de données pertinentes dans le contexte fourni pour répondre à cette question.
- **Missing Keywords**: ['7.67', '7,67']

### Test 6: Combien coûte la GAINE TPC COURONNE ROUGE D75 ?
- **Error/Response**: 
Réponse : Je suis désolé, mais je ne peux pas fournir une réponse précise à votre question car le document que vous avez fourni ne contient pas de données sur le coût de la GAINE TPC COURONNE ROUGE D75. Il contient plutôt des informations sur des mini pelles, des déboursés sec, des prix de matériaux et des coûts de cotraitance et de sous-traitance. Si vous avez d'autres informations ou si vous pouvez fournir un document plus précis, je serais heureux de vous aider.
- **Missing Keywords**: ['44.46', '44,46']

### Test 7: Quel est le coût de la MINI PELLE 8/10T ?
- **Error/Response**: 
Réponse : Il est difficile de déterminer le coût de la MINI PELLE 8/10T avec précision, car les sources fournies ne contiennent pas de données spécifiques sur ce modèle de mini pelle. Cependant, en examinant les données des calculs de prix, il est possible de déduire que le coût d'un équipement similaire peut varier entre 308 EUR et 504 EUR.
- **Missing Keywords**: ['352']

### Test 8: Quel est le coût de la PELLE 21T ?
- **Error/Response**: 
Réponse : Le coût de la PELLE 21T n'est pas spécifié dans le contexte fourni.
- **Missing Keywords**: ['800']

### Test 9: Quel est le prix de la TETE SECURITE Ø 500 COMPLETE ?
- **Error/Response**: 
Réponse : Je suis désolé, mais je ne peux pas trouver de prix pour la TETE SECURITE Ø 500 COMPLETE dans le contexte fourni. Il est possible que ce produit soit absent de la liste.
- **Missing Keywords**: ['193.94', '193,94']

### Test 10: Combien coûte un BURIN 350MM REAFFUTABLE ?
- **Error/Response**: 
Réponse : Selon les données de calcul de prix de la feuille 2 de votre fichier, le prix d'un BURIN 350MM REAFFUTABLE varie entre les années suivantes :

- 2021 : 1 000,00 EUR
- 2022 : 1 000,00 EUR
- 2023 : 1 000,00 EUR
- 2024 : 1 000,00 EUR
- 2025 : 1 000,00 EUR
- 2026 : 1 000,00 EUR
- 2027 : 1 000,00 EUR
- 2028 : 1 000,00 EUR
- 2029 : 1 000,00 EUR
- 2030 : 1 000,00 EUR

Il est donc possible que le prix d'un BURIN 350MM REAFFUTABLE soit de 1 000,00 EUR dans n'importe quelle année entre 2021 et 2030.
- **Missing Keywords**: ['7.20', '7,20']

### Test 11: Donnez-moi les tarifs des tuyaux d'assainissement béton.
- **Error/Response**: 
Réponse : Les tarifs des tuyaux d'assainissement béton sont disponibles sur la feuille 2 du document. Les tarifs sont donnés dans les lignes suivantes :

* Les tarifs des tuyaux de 100 mm de diamètre sont donnés dans les lignes 1881 à 1890.
* Les tarifs des tuyaux de 150 mm de diamètre sont donnés dans les lignes 2021 à 2030.
* Les tarifs des tuyaux de 200 mm de diamètre sont donnés dans les lignes 201 à 210.
* Les tarifs des tuyaux de 300 mm de diamètre sont donnés dans les lignes 451 à 460.
* Les tarifs des tuyaux de 400 mm de diamètre sont donnés dans les lignes 251 à 260.
* Les tarifs des tuyaux de 500 mm de diamètre sont donnés dans les lignes 111 à 120.
- **Missing Keywords**: ['139', '28.2', '38.2', '54.49', '70.73']

### Test 12: Quels sont les coûts des différents personnels de chantier ?
- **Error/Response**: 
Réponse : Les coûts des différents personnels de chantier ne sont pas spécifiés dans le contexte fourni. Cependant, il est possible de trouver des informations sur les compétences et les certifications des personnels de l'entreprise dans les sections suivantes :

- Présentation de l'entreprise, historique, compétences et CA (source [1])
- Nos certifications, valeurs et exigences (source [1])
- L'atelier mécanique et l'espace petit matériel (source [1])
- L'atelier carrosserie / peinture (source [1])

Pour des informations sur les coûts, il est recommandé de contacter directement l'entreprise.
- **Missing Keywords**: ['Chef', 'Maçon', 'Manoeuvre', '332', '256']

### Test 13: Quels sont les engins disponibles et leurs coûts ?
- **Error/Response**: 
Réponse :
Dans le contexte de l'atelier mécanique et de l'espace petit matériel, il n'y a pas de coûts spécifiés pour les engins disponibles. Cependant, il est possible de trouver des informations sur les coûts de main-d'œuvre, matériel et fournitures dans l'étude de prix [2].
- **Missing Keywords**: ['Pelle', 'Camion', '352', '480']

### Test 14: Quel est le code article pour le CIMENT FONDU SAC 25 KG ?
- **Error/Response**: 
Réponse : Il n'y a pas de code article pour le ciment fondu sac 25 kg dans le contexte fourni.
- **Missing Keywords**: ['2104010203', '8341']

### Test 16: Quel est le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE ?
- **Error/Response**: 
Réponse :
Le document fourni ne contient pas de données sur les prix des postes de CHEF CHANTIER et CHEF EQUIPE. Il est donc impossible de déterminer lequel est le plus cher entre les deux.
- **Missing Keywords**: ['332', 'identique', 'même prix']

### Test 17: Quel est le prix du TUYAU D1000 par rapport au D300 ?
- **Error/Response**: 
Réponse : Il n'y a pas de données pertinentes dans le contexte fourni pour comparer le prix du TUYAU D1000 par rapport au D300.
- **Missing Keywords**: ['139', '28.2']

### Test 18: De quoi parle le document WIAME VRD ?
- **Error/Response**: 
Réponse : Le document WIAME VRD parle de la bibliothèque générale de l'établissement WIAME. Il fournit des informations sur les livres, les périodiques, les documents numériques, les cartes et les plans, les CD et les DVD, les microfilms et les microfiches, les cartes sonores, les cartes de jeux, les cartes de jeux de société, les cartes de jeux de cartes, les cartes de jeux de cartes à collectionner, les cartes de jeux de cartes à collectionner numérotées, les cartes de jeux de cartes à collectionner non numérotées, les cartes de jeux de cartes à collectionner avec des illustrations, les cartes de jeux de cartes à collectionner avec des illustrations numérotées, les cartes de jeux de cartes à collectionner avec des illustrations non numérotées, les cartes de jeux de cartes à collectionner avec des illustrations numérotées et non numérotées, les cartes de jeux de cartes à collectionner avec des illustrations numérotées et non numérotées et non illustrées, les cartes de jeux de cartes à collectionner avec des illustrations numérotées et non numérotées et non illustrées et non numérotées, les cartes de jeux de cartes à collectionner avec des illustrations numérotées et non numérotées et non illustrées et non numérotées et non numérotées, les cartes de jeux de cartes à collectionner avec des illustrations numérotées et non numérotées et non illustrées et non numérotées et non numérotées et non numérotées et non numérotées, les cartes de jeux de cartes à collectionner avec des illustrations numérotées et non numérotées et non illustrées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numérotées et non numé
- **Missing Keywords**: ['présentation', 'entreprise', 'historique']

### Test 19: Qui est le fournisseur pour les tubes telecom ?
- **Error/Response**: 
Réponse : Nous n'avons pas de renseignement pertinent sur le fournisseur des tubes télécom dans le contexte fourni.
- **Missing Keywords**: ['WIAME', 'Fourniture']

### Test 20: Où se trouve le traitement de déchets ultimes ?
- **Error/Response**: 
Réponse : Je suis désolé, mais je ne trouve pas d'informations pertinentes sur le traitement de déchets ultimes dans le contexte fourni. Il est possible que ce sujet soit abordé dans d'autres parties de votre document, mais je ne peux pas le confirmer sans plus de détails.
- **Missing Keywords**: ['VERT LE GRAND']
