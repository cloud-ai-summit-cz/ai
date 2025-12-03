"""Mock data generator for Business Registry.

Provides realistic mock data for coffee shops and related businesses.
Uses a combination of curated data for known cities and seeded random
generation for flexibility in demos.
"""

import hashlib
import random
from datetime import datetime, timedelta
from typing import List, Optional

from models import (
    CompanySummary,
    CompanyProfile,
    CompanyFinancials,
    CompanyLocation,
    IndustryPlayer,
    NewsArticle,
)


def _seed_from_string(s: str) -> int:
    """Create a consistent seed from a string for repeatable randomization."""
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def _seeded_random(seed_str: str) -> random.Random:
    """Get a seeded random generator for consistent results."""
    rng = random.Random()
    rng.seed(_seed_from_string(seed_str))
    return rng


# ============================================================================
# Curated Data for Major Cities
# ============================================================================

COFFEE_CHAINS = {
    "vienna": [
        {
            "id": "comp-starbucks-at",
            "name": "Starbucks Austria",
            "legal_name": "AmRest Coffee s.r.o. (Starbucks AT)",
            "locations": 18,
            "employees": 320,
            "founded": 1971,
            "revenue": 28_000_000,
            "market_share": 15.2,
            "strengths": ["Brand recognition", "Consistent quality", "Mobile ordering"],
        },
        {
            "id": "comp-aida-at",
            "name": "Café Aida",
            "legal_name": "Aida Prousek KG",
            "locations": 25,
            "employees": 450,
            "founded": 1913,
            "revenue": 22_000_000,
            "market_share": 12.8,
            "strengths": ["Traditional Viennese", "Pastries", "Historic brand"],
        },
        {
            "id": "comp-demel-at",
            "name": "Demel",
            "legal_name": "K.u.K. Hofzuckerbäcker Demel",
            "locations": 3,
            "employees": 180,
            "founded": 1786,
            "revenue": 15_000_000,
            "market_share": 5.5,
            "strengths": ["Luxury positioning", "Tourism", "Historic heritage"],
        },
        {
            "id": "comp-coffeeshop-at",
            "name": "Coffeeshop Company",
            "legal_name": "Coffeeshop Company GmbH",
            "locations": 22,
            "employees": 280,
            "founded": 1999,
            "revenue": 18_000_000,
            "market_share": 10.5,
            "strengths": ["Modern atmosphere", "Good locations", "Franchise model"],
        },
        {
            "id": "comp-balthasar-at",
            "name": "Balthasar",
            "legal_name": "Balthasar Kaffeerösterei GmbH",
            "locations": 8,
            "employees": 65,
            "founded": 2012,
            "revenue": 4_500_000,
            "market_share": 2.8,
            "strengths": ["Specialty coffee", "Local roasting", "Hipster appeal"],
        },
    ],
    "prague": [
        {
            "id": "comp-starbucks-cz",
            "name": "Starbucks Czech Republic",
            "legal_name": "AmRest Coffee s.r.o.",
            "locations": 42,
            "employees": 520,
            "founded": 1971,
            "revenue": 35_000_000,
            "market_share": 18.5,
            "strengths": ["Brand recognition", "Premium positioning", "Loyalty program"],
        },
        {
            "id": "comp-costa-cz",
            "name": "Costa Coffee Czech",
            "legal_name": "Costa Coffee Czech Republic s.r.o.",
            "locations": 35,
            "employees": 380,
            "founded": 1971,
            "revenue": 28_000_000,
            "market_share": 14.2,
            "strengths": ["UK heritage", "Quality beans", "Store network"],
        },
        {
            "id": "comp-doubleshot-cz",
            "name": "Doubleshot",
            "legal_name": "Doubleshot s.r.o.",
            "locations": 5,
            "employees": 45,
            "founded": 2009,
            "revenue": 3_200_000,
            "market_share": 2.1,
            "strengths": ["Third wave coffee", "Own roastery", "Specialty focus"],
        },
        {
            "id": "comp-kavarna-cz",
            "name": "Café Louvre",
            "legal_name": "Café Louvre s.r.o.",
            "locations": 1,
            "employees": 85,
            "founded": 1902,
            "revenue": 5_800_000,
            "market_share": 1.8,
            "strengths": ["Historic location", "Tourism", "Traditional atmosphere"],
        },
    ],
    "munich": [
        {
            "id": "comp-starbucks-de",
            "name": "Starbucks Germany",
            "legal_name": "Starbucks Coffee Deutschland GmbH",
            "locations": 28,
            "employees": 420,
            "founded": 1971,
            "revenue": 42_000_000,
            "market_share": 12.8,
            "strengths": ["Global brand", "Consistent experience", "Digital ordering"],
        },
        {
            "id": "comp-einstein-de",
            "name": "Einstein Kaffee",
            "legal_name": "Einstein Kaffee GmbH",
            "locations": 15,
            "employees": 180,
            "founded": 2002,
            "revenue": 12_000_000,
            "market_share": 6.5,
            "strengths": ["German quality", "Local presence", "Fresh food"],
        },
        {
            "id": "comp-woerners-de",
            "name": "Woerner's",
            "legal_name": "Woerner's Café GmbH",
            "locations": 8,
            "employees": 95,
            "founded": 1910,
            "revenue": 7_500_000,
            "market_share": 3.2,
            "strengths": ["Bavarian tradition", "Pastries", "Local favorite"],
        },
    ],
}

# Districts within cities for location diversity
CITY_DISTRICTS = {
    "vienna": [
        "Innere Stadt", "Leopoldstadt", "Landstraße", "Wieden", "Margareten",
        "Mariahilf", "Neubau", "Josefstadt", "Alsergrund", "Favoriten",
    ],
    "prague": [
        "Prague 1", "Prague 2", "Prague 3", "Prague 4", "Prague 5",
        "Vinohrady", "Žižkov", "Holešovice", "Smíchov", "Karlín",
    ],
    "munich": [
        "Altstadt", "Maxvorstadt", "Schwabing", "Au-Haidhausen", "Sendling",
        "Neuhausen", "Bogenhausen", "Giesing", "Pasing", "Moosach",
    ],
}

# Generic company name templates for random generation
COFFEE_NAME_TEMPLATES = [
    "{city} Coffee Co.",
    "Café {adjective}",
    "The {adjective} Bean",
    "{name}'s Café",
    "{city} Roasters",
    "Urban Coffee {city}",
    "The Coffee House {district}",
]

ADJECTIVES = [
    "Golden", "Silver", "Royal", "Grand", "Central", "Modern", "Classic",
    "Premier", "Elite", "Cozy", "Sunny", "Green", "Blue", "Red",
]

OWNER_NAMES = [
    "Schmidt", "Müller", "Weber", "Fischer", "Meyer", "Wagner", "Becker",
    "Hoffman", "Novak", "Kowalski", "Horák", "Dvořák", "Svoboda",
]


def _generate_company_id(name: str, location: str) -> str:
    """Generate a consistent company ID."""
    slug = f"{name}-{location}".lower().replace(" ", "-").replace("'", "")[:30]
    hash_suffix = hashlib.md5(f"{name}{location}".encode()).hexdigest()[:6]
    return f"comp-{slug}-{hash_suffix}"


def _generate_random_company(city: str, industry: str, rng: random.Random) -> dict:
    """Generate a random but plausible company."""
    template = rng.choice(COFFEE_NAME_TEMPLATES)
    name = template.format(
        city=city.title(),
        adjective=rng.choice(ADJECTIVES),
        name=rng.choice(OWNER_NAMES),
        district=rng.choice(CITY_DISTRICTS.get(city.lower(), ["Center"])),
    )

    employees = rng.randint(15, 200)
    locations = rng.randint(1, max(1, employees // 20))
    founded = rng.randint(1990, 2022)

    return {
        "id": _generate_company_id(name, city),
        "name": name,
        "legal_name": f"{name} GmbH",
        "locations": locations,
        "employees": employees,
        "founded": founded,
        "revenue": employees * rng.randint(40000, 80000),
        "market_share": round(rng.uniform(0.5, 8.0), 1),
        "strengths": rng.sample(
            [
                "Good location", "Quality coffee", "Friendly staff", "Modern interior",
                "Local favorite", "Specialty drinks", "Good prices", "Fast service",
                "Cozy atmosphere", "Student discount", "Loyalty program", "Fresh pastries",
            ],
            k=rng.randint(2, 4),
        ),
    }


# ============================================================================
# Public API Functions
# ============================================================================


def search_companies(
    query: str,
    industry: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20,
) -> List[CompanySummary]:
    """Search for companies matching criteria."""
    results = []
    query_lower = query.lower()
    location_lower = (location or "").lower()

    # First, check curated data
    for city, companies in COFFEE_CHAINS.items():
        if location_lower and city not in location_lower and location_lower not in city:
            continue

        for comp in companies:
            if query_lower in comp["name"].lower() or query_lower in "coffee" or query_lower in "café":
                results.append(
                    CompanySummary(
                        company_id=comp["id"],
                        name=comp["name"],
                        industry=industry or "coffee_shops",
                        location=city.title(),
                        employees=comp["employees"],
                        founded_year=comp["founded"],
                        description=f"Major coffee chain with {comp['locations']} locations",
                    )
                )

    # If we have a specific location but no curated data, generate some
    if location_lower and len(results) < 5:
        rng = _seeded_random(f"search-{query}-{location}")
        for i in range(min(5, max_results - len(results))):
            comp = _generate_random_company(location, industry or "coffee", rng)
            results.append(
                CompanySummary(
                    company_id=comp["id"],
                    name=comp["name"],
                    industry=industry or "coffee_shops",
                    location=location.title(),
                    employees=comp["employees"],
                    founded_year=comp["founded"],
                    description=f"Local coffee establishment with {comp['locations']} locations",
                )
            )

    return results[:max_results]


def get_company_profile(company_id: str) -> Optional[CompanyProfile]:
    """Get detailed company profile."""
    # Search in curated data
    for city, companies in COFFEE_CHAINS.items():
        for comp in companies:
            if comp["id"] == company_id:
                return CompanyProfile(
                    company_id=comp["id"],
                    name=comp["name"],
                    legal_name=comp["legal_name"],
                    industry="coffee_shops",
                    sub_industry="cafes",
                    description=f"Established coffee chain with {comp['locations']} locations. "
                    f"Known for: {', '.join(comp['strengths'])}.",
                    headquarters=city.title(),
                    founded_year=comp["founded"],
                    employees=comp["employees"],
                    website=f"https://www.{comp['name'].lower().replace(' ', '').replace('é', 'e')}.com",
                    ownership_type="Private" if comp["locations"] < 20 else "Franchise",
                )

    # Generate for unknown company IDs
    rng = _seeded_random(company_id)
    name = f"Coffee Company {company_id[-6:]}"
    return CompanyProfile(
        company_id=company_id,
        name=name,
        legal_name=f"{name} GmbH",
        industry="coffee_shops",
        description="Local coffee establishment serving specialty coffee.",
        headquarters="Unknown",
        founded_year=rng.randint(1995, 2020),
        employees=rng.randint(20, 150),
        ownership_type="Private",
    )


def get_company_financials(company_id: str) -> Optional[CompanyFinancials]:
    """Get company financial data."""
    # Search in curated data
    for city, companies in COFFEE_CHAINS.items():
        for comp in companies:
            if comp["id"] == company_id:
                revenue = comp["revenue"]
                return CompanyFinancials(
                    company_id=comp["id"],
                    currency="EUR",
                    annual_revenue=revenue,
                    revenue_growth_yoy=round(random.uniform(-5, 15), 1),
                    gross_margin=round(random.uniform(55, 70), 1),
                    operating_margin=round(random.uniform(8, 18), 1),
                    net_margin=round(random.uniform(5, 12), 1),
                    fiscal_year_end="December",
                    notes="Estimated figures based on industry averages",
                )

    # Generate for unknown companies
    rng = _seeded_random(company_id)
    return CompanyFinancials(
        company_id=company_id,
        currency="EUR",
        annual_revenue=rng.randint(500_000, 10_000_000),
        revenue_growth_yoy=round(rng.uniform(-10, 20), 1),
        gross_margin=round(rng.uniform(50, 70), 1),
        operating_margin=round(rng.uniform(5, 15), 1),
        notes="Estimated figures",
    )


def get_company_locations(
    company_id: str,
    city: Optional[str] = None,
) -> List[CompanyLocation]:
    """Get company locations."""
    results = []

    # Search in curated data
    for city_name, companies in COFFEE_CHAINS.items():
        if city and city.lower() not in city_name:
            continue

        for comp in companies:
            if comp["id"] == company_id:
                districts = CITY_DISTRICTS.get(city_name, ["Center"])
                rng = _seeded_random(f"locations-{company_id}")

                for i in range(comp["locations"]):
                    district = districts[i % len(districts)]
                    results.append(
                        CompanyLocation(
                            location_id=f"loc-{company_id[-6:]}-{i:03d}",
                            company_id=company_id,
                            name=f"{comp['name']} {district}",
                            address=f"{rng.randint(1, 200)} {district} Street",
                            city=city_name.title(),
                            country="Austria" if city_name == "vienna" else "Czech Republic" if city_name == "prague" else "Germany",
                            location_type="Store",
                            size_sqm=rng.randint(60, 200),
                            employees=comp["employees"] // comp["locations"],
                        )
                    )

                return results

    # Generate for unknown companies
    rng = _seeded_random(f"locations-{company_id}")
    loc_count = rng.randint(1, 5)
    for i in range(loc_count):
        results.append(
            CompanyLocation(
                location_id=f"loc-{company_id[-6:]}-{i:03d}",
                company_id=company_id,
                name=f"Location {i + 1}",
                address=f"{rng.randint(1, 200)} Main Street",
                city=city or "Unknown",
                country="Unknown",
                location_type="Store",
                size_sqm=rng.randint(50, 150),
            )
        )

    return results


def get_industry_players(
    industry: str,
    region: str,
    limit: int = 10,
) -> List[IndustryPlayer]:
    """Get top industry players in a region."""
    results = []
    region_lower = region.lower()

    # Check curated data
    for city, companies in COFFEE_CHAINS.items():
        if city in region_lower or region_lower in city:
            for rank, comp in enumerate(sorted(companies, key=lambda x: x["market_share"], reverse=True), 1):
                results.append(
                    IndustryPlayer(
                        company_id=comp["id"],
                        name=comp["name"],
                        market_share=comp["market_share"],
                        rank=rank,
                        location_count=comp["locations"],
                        strengths=comp["strengths"],
                        founded_year=comp["founded"],
                    )
                )

    # If no curated data, generate some players
    if not results:
        rng = _seeded_random(f"players-{industry}-{region}")
        for rank in range(1, min(limit + 1, 8)):
            comp = _generate_random_company(region, industry, rng)
            results.append(
                IndustryPlayer(
                    company_id=comp["id"],
                    name=comp["name"],
                    market_share=round(25 / rank + rng.uniform(-2, 2), 1),
                    rank=rank,
                    location_count=comp["locations"],
                    strengths=comp["strengths"],
                    founded_year=comp["founded"],
                )
            )

    return results[:limit]


def get_company_news(
    company_id: str,
    days_back: int = 90,
) -> List[NewsArticle]:
    """Get recent news about a company."""
    results = []
    rng = _seeded_random(f"news-{company_id}")

    # Find company name
    company_name = "Coffee Company"
    for city, companies in COFFEE_CHAINS.items():
        for comp in companies:
            if comp["id"] == company_id:
                company_name = comp["name"]
                break

    # Generate mock news articles
    news_templates = [
        ("{company} Announces Expansion Plans", "positive"),
        ("{company} Reports Strong Quarterly Results", "positive"),
        ("{company} Opens New Location in {district}", "positive"),
        ("{company} Launches Sustainability Initiative", "positive"),
        ("{company} Faces Increased Competition", "neutral"),
        ("{company} Updates Menu with Seasonal Offerings", "neutral"),
        ("{company} CEO Discusses Future Strategy", "neutral"),
        ("{company} Partners with Local Suppliers", "positive"),
    ]

    sources = [
        "Business Weekly", "Coffee Industry News", "Local Times",
        "Economic Review", "Food & Beverage Journal", "City Business Report",
    ]

    districts = ["downtown", "city center", "business district", "shopping area"]

    num_articles = rng.randint(2, 6)
    base_date = datetime.now()

    for i in range(num_articles):
        template, sentiment = rng.choice(news_templates)
        title = template.format(
            company=company_name,
            district=rng.choice(districts),
        )
        pub_date = base_date - timedelta(days=rng.randint(1, days_back))

        results.append(
            NewsArticle(
                article_id=f"news-{company_id[-6:]}-{i:03d}",
                company_id=company_id,
                title=title,
                source=rng.choice(sources),
                published_date=pub_date.strftime("%Y-%m-%d"),
                summary=f"Article about {company_name}'s recent developments in the coffee industry.",
                sentiment=sentiment,
            )
        )

    return sorted(results, key=lambda x: x.published_date, reverse=True)
