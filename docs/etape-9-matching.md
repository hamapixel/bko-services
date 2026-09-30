# Étape 9 — Matching géographique et offres privées

Le matching est lancé automatiquement lorsqu'un client vérifié crée une demande dans une zone déjà structurée. Une relance manuelle reste disponible pour l'administration sur les demandes en attente. Le moteur n'examine que les prestataires qui remplissent **toutes** les conditions métier : compte actif, rôle `PROVIDER`, téléphone vérifié, profil prestataire vérifié, disponibilité active, métier demandé actif et abonnement compatible avec le type de demande.

## Ordre de recherche

Pour une demande rattachée à un quartier validé, l'ordre géographique est :

1. **Même métier obligatoire** — aucun prestataire d'un autre métier n'entre dans le matching.
2. **Quartier demandé prioritaire** — les prestataires ayant déclaré exactement ce quartier sont examinés en premier.
3. **Même commune en deuxième choix** — les prestataires d'autres quartiers actifs de la même commune peuvent compléter les offres. Le comportement historique qui peut réserver une place à la même commune est conservé.
4. **Déplacement inter-commune en troisième choix** — seulement s'il reste encore une place, un prestataire situé dans une autre commune peut être proposé s'il a explicitement ajouté la commune demandée dans ses `travel_communes`.

Un prestataire vérifié peut modifier ses communes de déplacement depuis son profil via `PATCH /api/v1/providers/travel-communes/`. Ce choix est volontaire : le système ne diffuse pas automatiquement une demande à tous les prestataires d'une ville ou d'une région. Une modification des communes de déplacement peut relancer les demandes compatibles qui attendaient encore un prestataire.

Le moteur crée au maximum **3 offres pour une demande normale** et **5 pour une urgence**. Dans chaque niveau, l'ordre reste déterministe : date de vérification du prestataire puis UUID.

## Attribution unique

Toutes les offres sont privées : chaque prestataire ne voit que ses propres offres. Au moment de l'acceptation, l'éligibilité complète est revérifiée, y compris le métier, la disponibilité, l'abonnement et la couverture géographique. Pour une offre inter-commune, la commune cible doit encore être présente dans les communes de déplacement autorisées du prestataire.

L'acceptation est protégée par une transaction PostgreSQL et un verrou sur la demande. **Le premier prestataire qui accepte gagne** : la demande passe à `ACCEPTED`, son profil devient `assigned_provider`, son offre passe à `ACCEPTED` et toutes les autres offres encore en attente passent immédiatement à `CANCELLED`. Les autres prestataires reçoivent une notification indiquant que la demande a déjà été attribuée.

## Confidentialité des offres

Avant attribution, l'offre expose uniquement les informations nécessaires à la décision : métier, quartier, commune, priorité, date et niveau de matching (`QUARTIER`, `COMMUNE` ou `DEPLACEMENT`). Le titre libre, la description, l'adresse précise et le téléphone du client restent masqués jusqu'à l'acceptation réussie.

| Méthode | Route | Accès |
| --- | --- | --- |
| GET | `/api/v1/providers/offers/` | Ses offres en attente seulement |
| GET | `/api/v1/providers/offers/<uuid>/` | Détail d'une offre qui lui appartient |
| POST | `/api/v1/providers/offers/<uuid>/accept/` | Accepter sa propre offre |
| PATCH | `/api/v1/providers/travel-communes/` | Modifier ses communes de déplacement autorisées |

## Demandes sans candidat

Si aucun prestataire compatible n'est trouvé, la demande reste `SEARCHING` et l'administration est notifiée. Le matching peut reprendre lorsqu'un prestataire compatible :

- devient disponible ;
- obtient ou renouvelle un abonnement ;
- libère une capacité d'intervention ;
- ajoute la commune cible à ses déplacements autorisés.

Les zones non encore structurées restent d'abord `LOCATION_PENDING` jusqu'à leur rattachement à un quartier actif par l'administration ; le matching démarre ensuite.

## Vérifications

Les tests couvrent notamment : même métier, priorité quartier → commune → déplacement autorisé, absence de diffusion inter-commune sans consentement, limites 3/5, relance automatique et attribution atomique avec annulation des offres concurrentes. La suite PostgreSQL complète et la CI doivent rester vertes avant toute fusion dans `main`.
