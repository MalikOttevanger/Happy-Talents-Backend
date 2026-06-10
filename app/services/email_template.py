"""Fixed proposal-email template, ported from the frontend `proposalEmail.ts`.

Assembles the full proposal email: the LLM-written `intro_html` (opening +
"Behoefte") followed by the fixed parts (candidate blocks, rate paragraph, next
steps, sign-off). The branded hand-out link lives in the intro prompt.
"""

from html import escape

from app.schemas.analysis import Opdracht
from app.schemas.matching import Candidate


def _first_name(full: str) -> str:
    """Return the first word of a full name (falls back to the input)."""
    parts = (full or "").strip().split()
    return parts[0] if parts else full


def _format_rate(uurtarief: int | str | None) -> str:
    """Render an hourly rate as a euro string."""
    if isinstance(uurtarief, int):
        return f"€ {uurtarief},-"
    return escape(str(uurtarief)) if uurtarief else "in overleg"


def _duration_phrase(opdracht: Opdracht) -> str | None:
    """Derive a human phrase for the assignment duration, or None if unknown."""
    if opdracht.startdatum and opdracht.einddatum:
        return f"{opdracht.startdatum} t/m {opdracht.einddatum}"
    if opdracht.einddatum:
        return f"tot {opdracht.einddatum}"
    return None


def _candidate_block(candidate: Candidate, index: int, is_primary: bool) -> str:
    """Render one candidate as a heading + bullet list."""
    role = candidate.specialisme or "Interim professional"
    skills = ", ".join((candidate.competenties or [])[:4])
    items = [f"<li><strong>Ervaring:</strong> {escape(candidate.matchuitleg)}</li>"]
    if skills:
        items.append(
            f"<li><strong>Eigenschappen:</strong> Sterk in {escape(skills)}. "
            "Zelfstartend, hands-on en gewend om snel te schakelen in een dynamische "
            "omgeving.</li>"
        )
    else:
        items.append(
            "<li><strong>Eigenschappen:</strong> Zelfstartend, hands-on en gewend om "
            "snel te schakelen.</li>"
        )
    locatie_suffix = f", flexibel inzetbaar vanuit {escape(candidate.locatie)}" if candidate.locatie else ""
    items.append(
        f"<li><strong>Beschikbaarheid:</strong> {escape(candidate.beschikbaarheid)}{locatie_suffix}.</li>"
    )
    if not is_primary:
        items.append(
            "<li><strong>Rol:</strong> Ondersteunt op projectbasis waar extra "
            "capaciteit of specialisme gewenst is.</li>"
        )
    return f"<p><strong>{index + 1}. {escape(candidate.naam)} ({escape(role)})</strong></p>\n<ul>{''.join(items)}</ul>"


def build_proposal_email(
    intro_html: str,
    candidates: list[Candidate],
    klant_naam: str,
    klant_bedrijf: str,
    opdracht: Opdracht,
) -> tuple[str, str]:
    """Assemble the proposal email and return (subject, body_html)."""
    rol = opdracht.functietitel or "interim professional"
    locatie = opdracht.locatie or "de gewenste locatie"
    duur = _duration_phrase(opdracht)
    primary = candidates[0]
    overige = candidates[1:]

    subject = f"Voorstel interim {rol} — {klant_bedrijf}"

    candidate_blocks = "\n".join(
        _candidate_block(c, i, i == 0) for i, c in enumerate(candidates)
    )

    aantal = "de volgende kandidaat" if len(candidates) == 1 else f"{len(candidates)} kandidaten"

    duur_clause = f" voor {duur}" if duur else " voor de gehele opdrachtperiode"
    rate_sentence = (
        f"<p>Wij stellen voor om {escape(_first_name(primary.naam))} in te zetten"
        f"{duur_clause} tegen een uurtarief van <strong>{_format_rate(primary.uurtarief)} "
        "excl. btw</strong>."
    )
    if overige:
        namen = " en ".join(_first_name(c.naam) for c in overige)
        verb = "zal" if len(overige) == 1 else "zullen"
        rate_sentence += (
            f" {escape(namen)} {verb} op projectbasis ondersteunen tegen vergelijkbare tarieven."
        )
    rate_sentence += "</p>"

    body = f"""{intro_html}

<p><strong>Kandidaten</strong><br/>
Op basis van deze behoeften stellen wij graag {aantal} voor:</p>

{candidate_blocks}

{rate_sentence}

<p>De inzet is gebaseerd op de gewenste aanwezigheid in {escape(locatie)}, waarbij \
reiskosten in overleg worden belast.</p>

<p><strong>Next steps</strong><br/>
Gezien de gewenste startdatum en inwerkperiode, stellen we voor om zeer op korte \
termijn kennis te maken.</p>

<p>We horen graag wat je van het voorstel vindt en of een kennismaking volgende \
week een mogelijkheid is.</p>

<p>Met vriendelijke groet,</p>"""

    return subject, body
