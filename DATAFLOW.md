# Happy Talents — Dataflow

End-to-end flow of the intake application, from login to a finished Gmail draft.
Consistent with the endpoints in `API.md` and the data model in `DATABASE.md`.
The whole flow is **user-triggered** — there are no scheduled jobs.

## Sequence diagram

```mermaid
sequenceDiagram
    participant U as Gebruiker
    participant FE as Frontend
    participant BE as Backend
    participant DB as Supabase
    participant PL as Plaud
    participant AI as Claude
    participant GM as Gmail
    participant AC as Active Campaign

    Note over U,DB: Inloggen en overzicht
    U->>FE: Open app
    FE->>BE: Login via Google SSO
    BE-->>FE: Sessie (JWT)
    FE->>BE: GET /api/v1/intakes
    BE->>DB: Haal intakes op
    DB-->>FE: Kanban-overzicht

    Note over U,BE: Nieuwe intake starten
    U->>FE: Plaud-link + klantgegevens invoeren
    FE->>BE: POST /api/v1/intakes
    BE->>DB: Job opslaan (processing)
    BE-->>FE: intake_id

    Note over BE,AI: Verwerking (async, op de backend)
    BE->>PL: Transcript ophalen
    PL-->>BE: Transcript
    BE->>AI: Behoefte uit transcript halen
    AI-->>BE: Opdracht-samenvatting
    BE->>AI: Passende rol kiezen
    AI-->>BE: type_rol
    BE->>DB: Interimmers met die rol ophalen
    DB-->>BE: Kandidaten
    BE->>AI: Kandidaten scoren en rangschikken
    AI-->>BE: Top-3 + aanbeveling
    BE->>DB: Shortlist opslaan (review)

    Note over U,FE: Resultaat bekijken
    FE->>BE: GET /api/v1/intakes/{id}
    BE-->>FE: Status review + shortlist
    U->>FE: Shortlist en onderbouwing bekijken

    Note over U,DB: Voorstel opstellen
    U->>FE: Kandidaten kiezen
    FE->>BE: POST /api/v1/proposals
    BE->>AI: Persoonlijke intro schrijven
    AI-->>BE: Intro-tekst
    BE->>DB: Voorstel opslaan
    BE-->>FE: Onderwerp + mailtekst

    Note over U,GM: Concept in Gmail zetten
    U->>FE: Tekst bevestigen of aanpassen
    FE->>BE: POST /api/v1/gmail/drafts
    BE->>GM: Handtekening lezen
    GM-->>BE: Handtekening
    BE->>GM: Concept-mail aanmaken
    GM-->>BE: gmail_draft_id
    BE->>DB: gmail_draft_id opslaan
    BE-->>FE: Concept staat klaar in Gmail

    Note over U,AC: Afronden
    U->>GM: Concept nakijken en zelf versturen
    U->>FE: Intake markeren als verzonden
    FE->>BE: PATCH /api/v1/intakes/{id} (verzonden)
    BE->>AC: Notitie op klantcontact (voorlopig)
    BE->>DB: Job bijwerken (verzonden)
```

## Notes

- **Login & overview.** The user logs in via Google SSO (Supabase Auth); the
  frontend loads the kanban overview of intakes.
- **Async processing.** Starting an intake returns an `intake_id` immediately; the
  pipeline (transcript → analysis → role selection → candidate query → ranking) runs
  on the backend. The frontend polls `GET /api/v1/intakes/{id}` until status `review`.
- **Matching reads from Supabase.** Interimmers are queried from Supabase; how that
  data is populated from Active Campaign is out of scope for now.
- **User sends the email.** The app only creates the Gmail draft (see technical plan
  §5.3). The user reviews and sends it manually, then marks the intake as `verzonden`.
- **Active Campaign note is provisional** (see `API.md` / technical plan §12),
  triggered on completion.
