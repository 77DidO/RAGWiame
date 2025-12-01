# RAG Contextual Quality Report

- API URL: `http://localhost:8081/v1/chat/completions`
- Headers: `X-Use-RAG: true`

## Résumé

| ID | Nom | Contexte | Attendu (hint) |
|----|-----|----------|----------------|
| 1 | Prix TUYAU D1000 | CONTEXT_TUYAU_D1000 | ~139 EUR |
| 2 | Référence GAINE D90 | CONTEXT_GAINE_D90 | D90 • ~56.18 EUR |
| 3 | Résumé WIAME VRD | CONTEXT_WIAME_VRD | présentation de l'entreprise WIAME VRD |
| 4 | Localisation déchets ultimes | CONTEXT_DECHETS | VERT LE GRAND |

## Détails par cas

### Case 1: Prix TUYAU D1000

- Question : `Quel est le prix unitaire du TUYAU ASSAINISSEMENT BETON ARME D1000 ?`
- Contexte : `CONTEXT_TUYAU_D1000`
- Attendu (hint) : `~139 EUR`

**Réponse brute :**

```
Réponse : Le prix unitaire du TUYAU ASSAINISSEMENT BETON ARME D1000 est de 139.00 EUR.
```

### Case 2: Référence GAINE D90

- Question : `Quelle est la référence et le prix de la GAINE TPC COURONNE ROUGE D90 ?`
- Contexte : `CONTEXT_GAINE_D90`
- Attendu (hint) : `D90 • ~56.18 EUR`

**Réponse brute :**

```
Réponse : La référence de la GAINE TPC COURONNE ROUGE D90 est GAINE TPC COURONNE ROUGE D90 et son prix unitaire est de 56.18 EUR.
```

### Case 3: Résumé WIAME VRD

- Question : `En une phrase, de quoi parle le document WIAME VRD ?`
- Contexte : `CONTEXT_WIAME_VRD`
- Attendu (hint) : `présentation de l'entreprise WIAME VRD`

**Réponse brute :**

```
Réponse : Le document WIAME VRD parle de l'entreprise spécialisée dans les travaux de voirie et réseaux divers, présentant son historique, ses compétences, ses références, ses valeurs, ses moyens humains et matériels, et son organisation des chantiers.
```

### Case 4: Localisation déchets ultimes

- Question : `Où se trouve le traitement des déchets ultimes ?`
- Contexte : `CONTEXT_DECHETS`
- Attendu (hint) : `VERT LE GRAND`

**Réponse brute :**

```
Réponse : Le traitement des déchets ultimes se trouve sur le site de VERT LE GRAND.
```
