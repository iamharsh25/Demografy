"""Shared constants and lookup data for the Demografy SQL agent."""

from __future__ import annotations

DEFAULT_LIMIT = 10

USER_FACING_UNANSWERABLE_REPLY = (
    "Sorry, I cannot answer this question. I do not have information for that. "
    "Could you try asking another question?"
)

STATE_ALIASES = {
    "act": "Australian Capital Territory",
    "australian capital territory": "Australian Capital Territory",
    "nsw": "New South Wales",
    "new south wales": "New South Wales",
    "nt": "Northern Territory",
    "northern territory": "Northern Territory",
    "qld": "Queensland",
    "queensland": "Queensland",
    "sa": "South Australia",
    "south australia": "South Australia",
    "tas": "Tasmania",
    "tasmania": "Tasmania",
    "vic": "Victoria",
    "victoria": "Victoria",
    "victorian": "Victoria",
    "wa": "Western Australia",
    "western australia": "Western Australia",
}

STATE_ABBREVIATIONS = {
    "Australian Capital Territory": "ACT",
    "New South Wales": "NSW",
    "Northern Territory": "NT",
    "Queensland": "Qld",
    "South Australia": "SA",
    "Tasmania": "Tas",
    "Victoria": "Vic",
    "Western Australia": "WA",
}

# Lowercase city/region phrases → canonical state name.
MAJOR_CITY_TO_STATE: dict[str, str] = {
    "sydney": "New South Wales",
    "newcastle": "New South Wales",
    "wollongong": "New South Wales",
    "melbourne": "Victoria",
    "geelong": "Victoria",
    "ballarat": "Victoria",
    "bendigo": "Victoria",
    "brisbane": "Queensland",
    "gold coast": "Queensland",
    "sunshine coast": "Queensland",
    "townsville": "Queensland",
    "cairns": "Queensland",
    "toowoomba": "Queensland",
    "adelaide": "South Australia",
    "perth": "Western Australia",
    "fremantle": "Western Australia",
    "hobart": "Tasmania",
    "launceston": "Tasmania",
    "canberra": "Australian Capital Territory",
    "darwin": "Northern Territory",
}

RANKABLE_METRICS = [
    {
        "keywords": ("migration", "migration footprint"),
        "column": "kpi_3_val",
        "alias": "migration_footprint",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("young family", "families"),
        "column": "kpi_10_val",
        "alias": "young_family_presence",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": (
            "prosperity",
            "prosperity score",
            "affluent",
            "affluence",
            "wealthy",
            "wealthiest",
            "rich",
            "well off",
            "blue chip",
            "socioeconomic",
            "advantaged",
            "high income",
        ),
        "column": "kpi_1_val",
        "alias": "prosperity_score",
        "intent": "ranked_metric",
        "order": "DESC",
    },
    {
        "keywords": (
            "learning",
            "education",
            "educated",
            "educational",
            "educational attainment",
            "schooling",
            "year 12",
            "qualification",
            "qualifications",
        ),
        "column": "kpi_4_val",
        "alias": "learning_level",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("social housing",),
        "column": "kpi_5_val",
        "alias": "social_housing_percentage",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("rental access", "affordability", "affordable"),
        "column": "kpi_7_val",
        "alias": "rental_access",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("home ownership", "resident equity"),
        "column": "kpi_6_val",
        "alias": "resident_equity",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("resident anchor", "stable", "stability"),
        "column": "kpi_8_val",
        "alias": "resident_anchor",
        "intent": "ranked_percent",
        "order": "DESC",
    },
]

# Shown as clarification chips when diversity ranking needs a state/city.
GEOGRAPHY_CLARIFICATION_CHIPS: tuple[str, ...] = (
    "Victoria",
    "New South Wales",
    "Queensland",
)

METRIC_CRITERIA: dict[str, str] = {
    "prosperity": (
        "Prosperity score is Demografy's way of summarising socioeconomic advantage for a suburb-level area.\n\n"
        "It runs from 0 to 100. Higher values generally point to more advantaged communities, while lower values suggest more socioeconomic pressure. "
        "It is useful as an affluence signal, but it is not the same thing as house price or income data.\n\n"
        "You could ask: \"show affluent suburbs in Victoria\" or \"compare prosperity across NSW suburbs\"."
    ),
    "diversity": (
        "Diversity index captures how culturally and linguistically mixed an area is.\n\n"
        "It runs from 0 to 1. Higher values mean the suburb has a broader mix of ancestry groups, while lower values suggest a more concentrated ancestry profile.\n\n"
        "You could ask: \"top diverse suburbs in NSW\" or \"diversity index in Forde\"."
    ),
    "migration": (
        "Migration footprint measures the share of residents with at least one overseas-born parent.\n\n"
        "It is shown as a percentage from 0 to 100%. Higher values usually indicate stronger first- or second-generation migrant community presence.\n\n"
        "You could ask: \"top suburbs by migration footprint in Victoria\"."
    ),
    "learning": (
        "Learning level is Demografy's education-attainment signal.\n\n"
        "It is based on Year 12 or equivalent attainment and is shown as a percentage from 0 to 100%. Higher values suggest a larger share of residents have completed that level of education.\n\n"
        "You could ask: \"educated suburbs in NSW\" or \"average education in Victoria\"."
    ),
    "social_housing": (
        "Social housing measures the share of households in public or community housing.\n\n"
        "It is shown as a percentage from 0 to 100%. Higher values indicate a larger social-housing presence in the area.\n\n"
        "You could ask: \"suburbs with social housing above 20%\"."
    ),
    "home_ownership": (
        "Home ownership, also called resident equity, measures the share of households owned outright or with a mortgage.\n\n"
        "It is shown as a percentage from 0 to 100%. Higher values can indicate a stronger owner-occupier base, but it does not tell you current property prices.\n\n"
        "You could ask: \"stable suburbs with high home ownership\"."
    ),
    "rental_access": (
        "Rental access is Demografy's rental-affordability proxy.\n\n"
        "It measures the share of renting households paying below $450 per week and is shown as a percentage from 0 to 100%. "
        "For example, a value of 60% means about 60% of renting households in that area are paying below $450/week. "
        "Higher values suggest lower-rent housing is more accessible in that area.\n\n"
        "It is not live rent listings, median rent, or median house-price data. You could ask: \"affordable rental suburbs in Queensland\" or \"compare rental access by state\"."
    ),
    "resident_anchor": (
        "Resident anchor is Demografy's population-stability signal.\n\n"
        "It measures the share of residents who lived at the same address five years earlier and is shown as a percentage from 0 to 100%. Higher values suggest a more settled, less transient community.\n\n"
        "You could ask: \"most stable suburbs in Australia\" or \"resident anchor in Queensland\"."
    ),
    "household_mobility": (
        "Household mobility captures households in more transitional living situations.\n\n"
        "It is shown as an index from 0 to 1. Higher values suggest more household movement or transition in the area.\n\n"
        "You could ask: \"suburbs with high household mobility\"."
    ),
    "young_family": (
        "Young family presence is the share of residents aged 0 to 14.\n\n"
        "It is shown as a percentage from 0 to 100%. Higher values suggest a stronger concentration of children and young-family households.\n\n"
        "You could ask: \"best suburbs for young families in Victoria\" or \"young family presence with high education\"."
    ),
    "population": (
        "Population is the estimated resident population for the suburb-level area.\n\n"
        "It is a headcount, not a percentage or index. You can use it to filter rankings or understand the scale of an area.\n\n"
        "You could ask: \"rental access in Queensland suburbs with at least 10,000 residents\"."
    ),
}

UNSUPPORTED_TOPIC_RULES = [
    {
        "name": "crime or safety",
        "terms": (
            "crime", "crimes", "criminal", "safety", "safe suburb", "safe suburbs",
            "safest", "dangerous", "violence", "burglary", "theft",
        ),
        "missing": "crime rates, safety incidents, or police-record data",
        "proxies": (
            "resident anchor for community stability",
            "social housing share for housing mix",
            "prosperity score for socioeconomic advantage",
        ),
        "example": "stable suburbs with high resident anchor in Victoria",
    },
    {
        "name": "schools",
        "terms": (
            "school ranking", "school rankings", "school rating", "school ratings",
            "best schools", "good schools", "naplan", "catchment", "school catchment",
        ),
        "missing": "school rankings, NAPLAN, catchments, or individual school performance",
        "proxies": (
            "learning level for education attainment",
            "young family presence for child-heavy communities",
            "prosperity score for socioeconomic context",
        ),
        "example": "suburbs in NSW with high young family presence and strong learning levels",
    },
    {
        "name": "transport or commute",
        "terms": (
            "transport", "public transport", "train station", "tram", "bus",
            "commute", "commuting", "travel time", "walkability", "walkable",
        ),
        "missing": "public transport access, commute times, station proximity, or walkability",
        "proxies": (
            "population for area scale",
            "resident anchor for stability",
            "rental access and home ownership for housing profile",
        ),
        "example": "compare rental access and home ownership by state",
    },
    {
        "name": "amenities",
        "terms": (
            "amenity", "amenities", "cafes", "restaurants", "shops", "shopping",
            "parks", "beach", "hospital", "hospitals", "healthcare", "doctor", "clinic",
        ),
        "missing": "amenities, hospitals, healthcare access, retail, parks, or lifestyle-location data",
        "proxies": (
            "population for suburb scale",
            "prosperity score for socioeconomic context",
            "resident anchor for settled-community signal",
        ),
        "example": "affluent suburbs in Victoria",
    },
    {
        "name": "forecast or growth",
        "terms": (
            "forecast", "forecasts", "predict", "prediction", "future growth",
            "capital growth", "growth potential", "investment growth", "next hotspot", "hotspot",
        ),
        "missing": "forecasts, investment predictions, capital-growth projections, or future hotspot modelling",
        "proxies": (
            "prosperity score for socioeconomic strength",
            "resident anchor for stability",
            "young family presence for demographic momentum",
            "home ownership for owner-occupier base",
        ),
        "example": "suburbs with high prosperity and high young family presence in Queensland",
    },
    {
        "name": "income or employment",
        "terms": (
            "income", "salary", "wage", "employment", "unemployment",
            "jobs", "job market", "occupation",
        ),
        "missing": "direct income, salary, job-market, occupation, or unemployment data",
        "proxies": (
            "prosperity score for socioeconomic advantage",
            "learning level for education attainment",
            "home ownership for resident equity",
        ),
        "example": "affluent suburbs in NSW",
    },
    {
        "name": "live listings",
        "terms": (
            "listing", "listings", "available rentals", "rental listings", "for sale",
            "open homes", "auction", "auctions", "domain.com", "realestate.com",
        ),
        "missing": "live property listings, homes for sale, rental listings, auctions, or open-home data",
        "proxies": (
            "rental access for lower-rent housing share",
            "home ownership for owner-occupier profile",
            "prosperity score for socioeconomic context",
        ),
        "example": "affordable rental suburbs in Victoria",
    },
]

# Tokens that must never appear in a place name extracted from a question.
_PLACE_TAIL_BLACKLIST = frozenset({
    "suburb", "suburbs", "area", "areas", "sa2", "sa3", "the suburb",
    "this suburb", "that suburb", "australia", "nationwide", "country",
    "prosperity", "prosperity score", "diversity", "diversity index",
    "migration", "migration footprint", "learning", "learning level",
    "education", "social housing", "home ownership", "resident equity",
    "rental access", "affordability", "resident anchor", "stability",
    "household mobility", "young family", "young families", "population",
})

# Filler words stripped when detecting a state-only follow-up.
_FOLLOWUP_FILLERS = frozenset({
    "what", "about", "and", "now", "how", "for", "the", "please", "tell",
    "me", "also", "then", "so", "ok", "okay", "hey", "plus", "again", "in",
    "of", "to", "from", "on", "show",
})

_AFFIRMATIVE_FOLLOWUPS = frozenset({
    "yes", "yep", "yeah", "please", "yes please", "yes, please",
    "sure", "sure please", "ok", "okay", "go ahead", "do it",
})
