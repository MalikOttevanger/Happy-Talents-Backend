"""Development-only interimmer seed.

Used by the interimmers repository ONLY when Supabase is not configured, so the
matching endpoint produces results during local development before the
`interimmers` table is provisioned. In production this is never used — data comes
from Supabase (synced from Active Campaign). Derived from the original n8n sample
pool, aligned to the DATABASE.md `interimmers` shape (rate bands collapsed to a
representative integer).
"""

from app.schemas.interimmer import Interimmer

# (id, naam, type_rol, provincie, uurtarief, uren_beschikbaar, werklocatie, max_reistijd, eigen_rol)
_RAW = [
    ("exp_001", "Piet Rijlaarsdam", ["Content Marketeer"], "Noord-Holland", 85, "16 uur", "Maakt niet uit", "60 minuten", "Creative copywriter"),
    ("exp_002", "Henk van der Made", ["Online Marketeer", "Content Marketeer", "Marketing Manager", "Social Media Advertising specialist"], "Noord-Brabant", 85, "32 uur", "Hybride", "Maakt niet uit", "Project & Campagne Manager"),
    ("exp_003", "Sam van der Sluis-Jansen", ["Marketing Manager", "Marketing Lead", "Communicatie adviseur", "Interim Strateeg", "Interim Manager"], "Utrecht", 95, "32 uur", "Maakt niet uit", "60 minuten", "B2B marketing manager"),
    ("exp_005", "Mick Seelen", ["Marketing Manager", "Product Owner", "Marketing Lead", "Communicatie adviseur", "Interim Strateeg", "Interim Manager"], "Noord-Brabant", 105, "32 uur", "Maakt niet uit", "60 minuten", "Marketing Director"),
    ("exp_006", "Sanne Demirel", ["Interim Manager"], "Noord-Holland", 75, "40 uur", "Hybride", "60 minuten", "Merchandising planner"),
    ("exp_007", "Merijn van Maarseveen", ["Content Marketeer", "Communicatie adviseur", "Interim Strateeg"], "Zuid-Holland", 105, "32 uur", "Maakt niet uit", "60 minuten", "Creatief strateeg, merkstrateeg"),
    ("exp_008", "Teun de Beer", ["Communicatie adviseur"], "Utrecht", 75, "8 uur", "Maakt niet uit", "30 minuten", "Content manager"),
    ("exp_009", "Chanel Van den Heuvel", ["Online Marketeer", "Performance Marketeer"], "Noord-Brabant", 65, "16 uur", "Hybride", "30 minuten", ""),
    ("exp_010", "Kees van Norel", ["Marketing Manager", "Communicatie adviseur", "Interim Strateeg", "Interim Manager"], "Gelderland", 95, "8 uur", "Hybride", "30 minuten", "Marketing- en Communicatie projectleider"),
    ("exp_011", "Klaas Tielen", ["Product Owner", "Data-analist", "Marketing Automation specialist", "Interim Manager"], "Noord-Brabant", 85, "32 uur", "Hybride", "Maakt niet uit", "CRM, Loyalty, Business analyse"),
    ("exp_013", "Jaap Werker", ["Performance Marketeer", "Marketing Lead", "SEA specialist"], "Drenthe", 95, "8 uur", "Remote", "30 minuten", ""),
    ("exp_014", "Niek Pijpers", ["Content Marketeer"], "Gelderland", 75, "16 uur", "Maakt niet uit", "60 minuten", ""),
    ("exp_015", "Ferdi de Been", ["Online Marketeer", "Performance Marketeer", "Marketing Manager", "Marketing Lead", "Interim Strateeg", "Interim Manager"], "Noord-Brabant", 85, "16 uur", "Maakt niet uit", "60 minuten", "Interim Director"),
    ("exp_016", "Fleur Holtrop - de Joode", ["Marketing Manager", "Marketing Lead", "Interim Strateeg", "Interim Manager"], "Noord-Brabant", 105, "32 uur", "Hybride", "60 minuten", ""),
    ("exp_017", "Gerjanne Bijker", ["Online Marketeer", "Content Marketeer", "Marketing Manager", "Communicatie adviseur", "Social Media Advertising specialist", "Interim Strateeg"], "Friesland", 65, "32 uur", "Remote", "Maakt niet uit", "Marketingstrateeg"),
    ("exp_018", "Gerrit van Oene", ["Online Marketeer", "Content Marketeer"], "Noord-Holland", 65, "40 uur", "Hybride", "60 minuten", "Content manager"),
    ("exp_019", "Glenn Snel", ["Online Marketeer", "Growth Marketeer", "SEO specialist", "Interim Strateeg", "Interim Manager"], "Zuid-Holland", 95, "32 uur", "Hybride", "60 minuten", "CRO specialist"),
]


def _build(row) -> Interimmer:
    id_, naam, type_rol, provincie, tarief, uren, werklocatie, reistijd, eigen = row
    skills = [eigen] if eigen else []
    return Interimmer(
        id=id_,
        naam=naam,
        type_rol=type_rol,
        provincie=provincie,
        uurtarief=tarief,
        uren_beschikbaar=uren,
        werklocatie=werklocatie,
        max_reistijd=reistijd,
        skills=skills,
    )


DEV_INTERIMMERS: list[Interimmer] = [_build(row) for row in _RAW]
