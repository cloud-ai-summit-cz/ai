"""Mock data generator for Real Estate.

Provides realistic commercial property data for Brno, Vienna, and Prague.
Focused on coffee shop/café suitable locations.
"""

import hashlib
import random
from typing import List, Optional

from models import (
    CommercialProperty,
    RentalRates,
    FootTraffic,
    NearbyAmenity,
    LocationScore,
    VacancyRate,
    LocationComparison,
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
# Curated Property Data for Target Cities
# ============================================================================

CURATED_PROPERTIES = {
    "brno": [
        {
            "id": "brno-veveri-01",
            "address": "Veveří 42",
            "district": "Veveří",
            "city": "Brno",
            "country": "Czech Republic",
            "property_type": "retail",
            "size_sqm": 85,
            "monthly_rent_eur": 1_700,
            "available_date": "2025-03-01",
            "features": ["Street level", "Large windows", "Near tram stop", "Student area"],
            "condition": "basic",
            "lease_term_months": 36,
            "contact": "brno-properties@example.cz",
            "notes": "Former bakery, good natural light. High student foot traffic.",
        },
        {
            "id": "brno-veveri-02",
            "address": "Kounicova 15",
            "district": "Veveří",
            "city": "Brno",
            "country": "Czech Republic",
            "property_type": "cafe",
            "size_sqm": 120,
            "monthly_rent_eur": 2_400,
            "available_date": "2025-02-15",
            "features": ["Corner unit", "Outdoor seating possible", "Near university", "Basement storage"],
            "condition": "fitted",
            "lease_term_months": 60,
            "contact": "reality-veveri@example.cz",
            "notes": "Premium location near Masaryk University. Previous tenant was a café.",
        },
        {
            "id": "brno-kralovopole-01",
            "address": "Purkyňova 93",
            "district": "Královo Pole",
            "city": "Brno",
            "country": "Czech Republic",
            "property_type": "retail",
            "size_sqm": 95,
            "monthly_rent_eur": 1_900,
            "available_date": "2025-04-01",
            "features": ["Tech park area", "Parking available", "Modern building", "AC included"],
            "condition": "shell",
            "lease_term_months": 48,
            "contact": "techpark-leasing@example.cz",
            "notes": "Near BUT campus and tech companies. Growing area.",
        },
        {
            "id": "brno-centrum-01",
            "address": "Česká 12",
            "district": "Brno-střed",
            "city": "Brno",
            "country": "Czech Republic",
            "property_type": "retail",
            "size_sqm": 65,
            "monthly_rent_eur": 2_200,
            "available_date": "2025-01-15",
            "features": ["Prime pedestrian street", "Historic building", "High visibility"],
            "condition": "basic",
            "lease_term_months": 60,
            "contact": "centrum-reality@example.cz",
            "notes": "Main shopping street. Very high foot traffic but also high competition.",
        },
        {
            "id": "brno-zidenice-01",
            "address": "Gajdošova 58",
            "district": "Židenice",
            "city": "Brno",
            "country": "Czech Republic",
            "property_type": "retail",
            "size_sqm": 110,
            "monthly_rent_eur": 1_400,
            "available_date": "2025-02-01",
            "features": ["Residential area", "Parking", "Large space", "Affordable rent"],
            "condition": "basic",
            "lease_term_months": 36,
            "contact": "zidenice-reality@example.cz",
            "notes": "Gentrifying area. Lower rent but building local community.",
        },
    ],
    "vienna": [
        {
            "id": "vienna-neubau-01",
            "address": "Neubaugasse 28",
            "district": "Neubau",
            "city": "Vienna",
            "country": "Austria",
            "property_type": "retail",
            "size_sqm": 75,
            "monthly_rent_eur": 3_200,
            "available_date": "2025-03-01",
            "features": ["Trendy area", "High foot traffic", "Young demographic", "Near MuseumsQuartier"],
            "condition": "fitted",
            "lease_term_months": 60,
            "contact": "neubau-immobilien@example.at",
            "notes": "7th district, hipster neighborhood. Strong specialty coffee presence.",
        },
        {
            "id": "vienna-neubau-02",
            "address": "Burggasse 42",
            "district": "Neubau",
            "city": "Vienna",
            "country": "Austria",
            "property_type": "cafe",
            "size_sqm": 95,
            "monthly_rent_eur": 3_800,
            "available_date": "2025-02-15",
            "features": ["Corner location", "Outdoor seating", "Fully equipped kitchen", "Basement"],
            "condition": "turnkey",
            "lease_term_months": 60,
            "contact": "wien-gastro@example.at",
            "notes": "Former café, all equipment included. Ready to operate.",
        },
        {
            "id": "vienna-mariahilf-01",
            "address": "Mariahilfer Straße 88",
            "district": "Mariahilf",
            "city": "Vienna",
            "country": "Austria",
            "property_type": "retail",
            "size_sqm": 60,
            "monthly_rent_eur": 4_500,
            "available_date": "2025-04-01",
            "features": ["Major shopping street", "Highest foot traffic", "Premium location"],
            "condition": "shell",
            "lease_term_months": 120,
            "contact": "mariahilf-premium@example.at",
            "notes": "Vienna's busiest shopping street. Very expensive but maximum exposure.",
        },
        {
            "id": "vienna-leopoldstadt-01",
            "address": "Praterstraße 32",
            "district": "Leopoldstadt",
            "city": "Vienna",
            "country": "Austria",
            "property_type": "retail",
            "size_sqm": 85,
            "monthly_rent_eur": 2_600,
            "available_date": "2025-02-01",
            "features": ["Near Praterstern", "Diverse neighborhood", "Growing area", "Good transit"],
            "condition": "basic",
            "lease_term_months": 48,
            "contact": "leopoldstadt-immo@example.at",
            "notes": "2nd district, gentrifying. More affordable than 6th/7th.",
        },
        {
            "id": "vienna-josefstadt-01",
            "address": "Josefstädter Straße 55",
            "district": "Josefstadt",
            "city": "Vienna",
            "country": "Austria",
            "property_type": "retail",
            "size_sqm": 70,
            "monthly_rent_eur": 2_900,
            "available_date": "2025-03-15",
            "features": ["Residential upscale", "Local clientele", "Near university", "Quiet street"],
            "condition": "fitted",
            "lease_term_months": 60,
            "contact": "josefstadt-reality@example.at",
            "notes": "8th district, professional neighborhood. Good for regular customers.",
        },
    ],
    "prague": [
        {
            "id": "prague-karlin-01",
            "address": "Křižíkova 42",
            "district": "Karlín",
            "city": "Prague",
            "country": "Czech Republic",
            "property_type": "retail",
            "size_sqm": 90,
            "monthly_rent_eur": 2_800,
            "available_date": "2025-02-01",
            "features": ["Tech hub area", "Modern building", "Young professionals", "Near metro"],
            "condition": "fitted",
            "lease_term_months": 60,
            "contact": "karlin-properties@example.cz",
            "notes": "This is Cofilot's home district. Reference location.",
        },
    ],
}

# Rental rates by city and district
RENTAL_RATES = {
    "brno": {
        "brno-střed": {"avg": 28, "min": 22, "max": 38, "trend": "increasing", "yoy": 8.5},
        "veveří": {"avg": 22, "min": 18, "max": 28, "trend": "increasing", "yoy": 12.0},
        "královo pole": {"avg": 20, "min": 16, "max": 26, "trend": "increasing", "yoy": 10.5},
        "židenice": {"avg": 14, "min": 10, "max": 18, "trend": "stable", "yoy": 3.2},
        "černá pole": {"avg": 18, "min": 14, "max": 22, "trend": "stable", "yoy": 4.0},
    },
    "vienna": {
        "innere stadt": {"avg": 65, "min": 50, "max": 95, "trend": "stable", "yoy": 2.5},
        "neubau": {"avg": 42, "min": 35, "max": 55, "trend": "increasing", "yoy": 6.8},
        "mariahilf": {"avg": 55, "min": 42, "max": 75, "trend": "stable", "yoy": 3.2},
        "leopoldstadt": {"avg": 32, "min": 25, "max": 42, "trend": "increasing", "yoy": 9.5},
        "josefstadt": {"avg": 38, "min": 30, "max": 48, "trend": "stable", "yoy": 4.0},
    },
    "prague": {
        "prague 1": {"avg": 55, "min": 40, "max": 80, "trend": "stable", "yoy": 2.0},
        "karlín": {"avg": 32, "min": 25, "max": 42, "trend": "increasing", "yoy": 7.5},
        "vinohrady": {"avg": 38, "min": 30, "max": 50, "trend": "stable", "yoy": 4.5},
        "holešovice": {"avg": 28, "min": 22, "max": 38, "trend": "increasing", "yoy": 11.0},
    },
}

# Foot traffic estimates by district
FOOT_TRAFFIC = {
    "brno": {
        "brno-střed": {"daily": 45000, "peak": "12:00-13:00", "peak_count": 8500, "weekday": 48000, "weekend": 38000},
        "veveří": {"daily": 22000, "peak": "11:00-12:00", "peak_count": 4200, "weekday": 25000, "weekend": 15000},
        "královo pole": {"daily": 18000, "peak": "8:00-9:00", "peak_count": 3800, "weekday": 22000, "weekend": 10000},
        "židenice": {"daily": 12000, "peak": "17:00-18:00", "peak_count": 2500, "weekday": 13000, "weekend": 10000},
    },
    "vienna": {
        "innere stadt": {"daily": 120000, "peak": "14:00-15:00", "peak_count": 22000, "weekday": 110000, "weekend": 140000},
        "neubau": {"daily": 55000, "peak": "13:00-14:00", "peak_count": 9500, "weekday": 52000, "weekend": 62000},
        "mariahilf": {"daily": 85000, "peak": "15:00-16:00", "peak_count": 15000, "weekday": 78000, "weekend": 98000},
        "leopoldstadt": {"daily": 38000, "peak": "12:00-13:00", "peak_count": 6500, "weekday": 40000, "weekend": 34000},
    },
    "prague": {
        "karlín": {"daily": 32000, "peak": "12:00-13:00", "peak_count": 6200, "weekday": 38000, "weekend": 20000},
    },
}

# Location scores (pre-calculated for key districts)
LOCATION_SCORES = {
    "brno": {
        "veveří": {
            "overall": 78,
            "walkability": 82,
            "transit": 85,
            "business_density": 72,
            "competition_risk": 35,  # Lower = better
            "growth_potential": 85,
            "coffee_fit": 82,
            "notes": ["Strong student presence", "Growing tech sector", "Limited specialty coffee competition", "Cofilot-friendly demographic"],
        },
        "královo pole": {
            "overall": 72,
            "walkability": 68,
            "transit": 78,
            "business_density": 75,
            "competition_risk": 28,
            "growth_potential": 88,
            "coffee_fit": 75,
            "notes": ["Tech hub growth", "BUT university nearby", "Car-dependent some areas", "Office worker lunch crowd"],
        },
        "brno-střed": {
            "overall": 74,
            "walkability": 90,
            "transit": 92,
            "business_density": 85,
            "competition_risk": 65,
            "growth_potential": 60,
            "coffee_fit": 70,
            "notes": ["High competition from chains", "Tourist/shopper traffic", "Premium rents", "Saturated market"],
        },
        "židenice": {
            "overall": 62,
            "walkability": 65,
            "transit": 72,
            "business_density": 55,
            "competition_risk": 18,
            "growth_potential": 75,
            "coffee_fit": 58,
            "notes": ["Emerging area", "Lower income demographic", "Community building opportunity", "Risk of slow ramp-up"],
        },
    },
    "vienna": {
        "neubau": {
            "overall": 82,
            "walkability": 88,
            "transit": 85,
            "business_density": 80,
            "competition_risk": 55,
            "growth_potential": 72,
            "coffee_fit": 88,
            "notes": ["Perfect Cofilot demographic", "Strong specialty coffee scene", "High rent but justified", "Creative class hub"],
        },
        "mariahilf": {
            "overall": 75,
            "walkability": 85,
            "transit": 88,
            "business_density": 90,
            "competition_risk": 70,
            "growth_potential": 58,
            "coffee_fit": 72,
            "notes": ["Shopping focus over café culture", "Very high rents", "Tourist-heavy", "Chains dominate"],
        },
        "leopoldstadt": {
            "overall": 76,
            "walkability": 78,
            "transit": 82,
            "business_density": 68,
            "competition_risk": 40,
            "growth_potential": 82,
            "coffee_fit": 78,
            "notes": ["Gentrifying rapidly", "More affordable", "Diverse community", "Growing creative scene"],
        },
        "josefstadt": {
            "overall": 70,
            "walkability": 80,
            "transit": 75,
            "business_density": 65,
            "competition_risk": 45,
            "growth_potential": 62,
            "coffee_fit": 72,
            "notes": ["Residential focus", "Loyal local customers", "Quieter pace", "Professional demographic"],
        },
    },
}

# Nearby amenities templates
AMENITY_TEMPLATES = {
    "brno": {
        "veveří": [
            {"name": "Masaryk University - Faculty of Arts", "type": "university", "distance": 150, "relevance": "positive"},
            {"name": "Rebelbean", "type": "competitor", "distance": 400, "relevance": "negative"},
            {"name": "Tram Stop Grohova", "type": "transit", "distance": 80, "relevance": "positive"},
            {"name": "Student dormitory Vinařská", "type": "residential", "distance": 300, "relevance": "positive"},
            {"name": "Knihovna Jiřího Mahena", "type": "library", "distance": 500, "relevance": "positive"},
        ],
        "královo pole": [
            {"name": "Brno University of Technology", "type": "university", "distance": 200, "relevance": "positive"},
            {"name": "CEITEC Research Center", "type": "tech_office", "distance": 350, "relevance": "positive"},
            {"name": "Y Soft headquarters", "type": "tech_office", "distance": 280, "relevance": "positive"},
            {"name": "Industra Coffee", "type": "competitor", "distance": 600, "relevance": "negative"},
            {"name": "Metro Stop Technologický park", "type": "transit", "distance": 150, "relevance": "positive"},
        ],
    },
    "vienna": {
        "neubau": [
            {"name": "MuseumsQuartier", "type": "cultural", "distance": 400, "relevance": "positive"},
            {"name": "Jonas Reindl Coffee", "type": "competitor", "distance": 350, "relevance": "negative"},
            {"name": "Balthasar", "type": "competitor", "distance": 500, "relevance": "negative"},
            {"name": "U-Bahn Museumsquartier", "type": "transit", "distance": 300, "relevance": "positive"},
            {"name": "WU Executive Academy", "type": "university", "distance": 800, "relevance": "positive"},
            {"name": "Zentrales Verwaltungsgebäude", "type": "office", "distance": 450, "relevance": "positive"},
        ],
        "leopoldstadt": [
            {"name": "Praterstern Station", "type": "transit", "distance": 200, "relevance": "positive"},
            {"name": "WU Vienna", "type": "university", "distance": 600, "relevance": "positive"},
            {"name": "Prater", "type": "recreation", "distance": 400, "relevance": "positive"},
            {"name": "Starbucks Praterstern", "type": "competitor", "distance": 250, "relevance": "negative"},
        ],
    },
}

VACANCY_RATES = {
    "brno": {"retail": 4.2, "cafe": 3.8, "trend": "decreasing", "days_to_lease": 45},
    "vienna": {"retail": 6.5, "cafe": 5.2, "trend": "stable", "days_to_lease": 62},
    "prague": {"retail": 3.5, "cafe": 2.8, "trend": "decreasing", "days_to_lease": 38},
}


# ============================================================================
# Public API Functions
# ============================================================================


def search_commercial_properties(
    city: str,
    district: str | None = None,
    property_type: str | None = None,
    min_size_sqm: float | None = None,
    max_size_sqm: float | None = None,
    max_rent_eur: float | None = None,
) -> list[CommercialProperty]:
    """Search for commercial properties matching criteria."""
    city_lower = city.lower().strip()
    results = []

    # Get properties for the city
    properties = CURATED_PROPERTIES.get(city_lower, [])

    for prop in properties:
        # Apply filters
        if district and district.lower() not in prop["district"].lower():
            continue
        if property_type and property_type.lower() not in prop["property_type"].lower():
            if property_type.lower() not in ["retail", "cafe", "café", "coffee"]:
                continue
        if min_size_sqm and prop["size_sqm"] < min_size_sqm:
            continue
        if max_size_sqm and prop["size_sqm"] > max_size_sqm:
            continue
        if max_rent_eur and prop["monthly_rent_eur"] > max_rent_eur:
            continue

        results.append(
            CommercialProperty(
                id=prop["id"],
                address=prop["address"],
                district=prop["district"],
                city=prop["city"],
                country=prop["country"],
                property_type=prop["property_type"],
                size_sqm=prop["size_sqm"],
                monthly_rent_eur=prop["monthly_rent_eur"],
                price_per_sqm=round(prop["monthly_rent_eur"] / prop["size_sqm"], 2),
                available_date=prop["available_date"],
                features=prop["features"],
                condition=prop["condition"],
                lease_term_months=prop["lease_term_months"],
                contact=prop["contact"],
                notes=prop.get("notes"),
            )
        )

    return results


def get_rental_rates(
    city: str,
    district: str | None = None,
    property_type: str = "retail",
) -> RentalRates:
    """Get rental rate data for a location."""
    city_lower = city.lower().strip()
    district_lower = (district or "").lower().strip()

    city_rates = RENTAL_RATES.get(city_lower, {})

    # Find best matching district
    rates = None
    for dist_name, dist_rates in city_rates.items():
        if district_lower and district_lower in dist_name:
            rates = dist_rates
            break

    if not rates:
        # Use city average
        if city_rates:
            avg_rate = sum(r["avg"] for r in city_rates.values()) / len(city_rates)
            rates = {
                "avg": avg_rate,
                "min": avg_rate * 0.7,
                "max": avg_rate * 1.4,
                "trend": "stable",
                "yoy": 5.0,
            }
        else:
            rates = {"avg": 25, "min": 18, "max": 35, "trend": "stable", "yoy": 3.0}

    return RentalRates(
        location=f"{city.title()}" + (f" - {district.title()}" if district else ""),
        property_type=property_type,
        avg_rate_sqm_month=rates["avg"],
        min_rate=rates["min"],
        max_rate=rates["max"],
        trend=rates["trend"],
        yoy_change_percent=rates["yoy"],
        currency="EUR",
        data_quarter="Q4 2024",
    )


def get_foot_traffic(
    city: str,
    district: str | None = None,
) -> FootTraffic:
    """Get foot traffic data for a location."""
    city_lower = city.lower().strip()
    district_lower = (district or "").lower().strip()

    city_traffic = FOOT_TRAFFIC.get(city_lower, {})

    # Find best matching district
    traffic = None
    for dist_name, dist_traffic in city_traffic.items():
        if district_lower and district_lower in dist_name:
            traffic = dist_traffic
            break

    if not traffic:
        # Generate reasonable default
        rng = _seeded_random(f"traffic-{city}-{district}")
        traffic = {
            "daily": rng.randint(15000, 40000),
            "peak": "12:00-13:00",
            "peak_count": rng.randint(3000, 7000),
            "weekday": rng.randint(18000, 45000),
            "weekend": rng.randint(12000, 35000),
        }

    return FootTraffic(
        location=city.title(),
        district=district.title() if district else None,
        daily_average=traffic["daily"],
        peak_hour=traffic["peak"],
        peak_count=traffic["peak_count"],
        weekday_avg=traffic["weekday"],
        weekend_avg=traffic["weekend"],
        seasonal_variation="Higher in summer months (+15-20%)",
        measurement_source="Municipal pedestrian counters + estimation",
    )


def get_nearby_amenities(
    city: str,
    district: str,
    radius_meters: int = 500,
) -> list[NearbyAmenity]:
    """Get nearby amenities for a location."""
    city_lower = city.lower().strip()
    district_lower = district.lower().strip()

    city_amenities = AMENITY_TEMPLATES.get(city_lower, {})

    # Find matching district
    for dist_name, amenities in city_amenities.items():
        if dist_name in district_lower or district_lower in dist_name:
            return [
                NearbyAmenity(
                    name=a["name"],
                    type=a["type"],
                    distance_meters=a["distance"],
                    relevance=a["relevance"],
                    details=a.get("details"),
                )
                for a in amenities
                if a["distance"] <= radius_meters
            ]

    # Generate some amenities
    rng = _seeded_random(f"amenities-{city}-{district}")
    generic = [
        {"name": "Tram/Metro Stop", "type": "transit", "distance": rng.randint(50, 200), "relevance": "positive"},
        {"name": "Local Café", "type": "competitor", "distance": rng.randint(200, 500), "relevance": "negative"},
        {"name": "Office Building", "type": "office", "distance": rng.randint(100, 300), "relevance": "positive"},
    ]

    return [
        NearbyAmenity(
            name=a["name"],
            type=a["type"],
            distance_meters=a["distance"],
            relevance=a["relevance"],
        )
        for a in generic
    ]


def get_location_score(
    city: str,
    district: str,
) -> LocationScore:
    """Get composite location score for site evaluation."""
    city_lower = city.lower().strip()
    district_lower = district.lower().strip()

    city_scores = LOCATION_SCORES.get(city_lower, {})

    # Find matching district
    for dist_name, scores in city_scores.items():
        if dist_name in district_lower or district_lower in dist_name:
            return LocationScore(
                location=city.title(),
                district=district.title(),
                overall_score=scores["overall"],
                walkability=scores["walkability"],
                transit_access=scores["transit"],
                business_density=scores["business_density"],
                competition_risk=scores["competition_risk"],
                growth_potential=scores["growth_potential"],
                coffee_shop_fit=scores["coffee_fit"],
                notes=scores["notes"],
            )

    # Generate reasonable scores
    rng = _seeded_random(f"score-{city}-{district}")
    return LocationScore(
        location=city.title(),
        district=district.title(),
        overall_score=rng.randint(55, 75),
        walkability=rng.randint(60, 85),
        transit_access=rng.randint(55, 80),
        business_density=rng.randint(50, 75),
        competition_risk=rng.randint(30, 60),
        growth_potential=rng.randint(50, 75),
        coffee_shop_fit=rng.randint(55, 75),
        notes=["Data based on area characteristics", "Detailed assessment recommended"],
    )


def get_vacancy_rates(
    city: str,
    property_type: str = "retail",
) -> VacancyRate:
    """Get commercial vacancy rate data."""
    city_lower = city.lower().strip()
    property_lower = property_type.lower()

    city_vacancy = VACANCY_RATES.get(city_lower, VACANCY_RATES["brno"])

    rate_key = "cafe" if "cafe" in property_lower or "café" in property_lower else "retail"

    return VacancyRate(
        location=city.title(),
        property_type=property_type,
        vacancy_rate_percent=city_vacancy[rate_key],
        trend=city_vacancy["trend"],
        avg_time_to_lease_days=city_vacancy["days_to_lease"],
        available_units=int(city_vacancy[rate_key] * 25),  # Rough estimate
        data_quarter="Q4 2024",
    )


def compare_locations(
    locations: list[dict],
) -> LocationComparison:
    """Compare multiple locations for site selection.
    
    Args:
        locations: List of dicts with 'city' and 'district' keys
    """
    comparison = {}
    location_names = []

    for loc in locations:
        city = loc.get("city", "")
        district = loc.get("district", "")
        loc_name = f"{city.title()} - {district.title()}"
        location_names.append(loc_name)

        score = get_location_score(city, district)
        comparison[loc_name] = {
            "overall": score.overall_score,
            "walkability": score.walkability,
            "transit": score.transit_access,
            "competition_risk": 100 - score.competition_risk,  # Invert so higher = better
            "growth_potential": score.growth_potential,
            "coffee_fit": score.coffee_shop_fit,
        }

    # Find best overall
    best = max(comparison.items(), key=lambda x: x[1]["overall"])[0]

    # Generate recommendation
    if "Brno" in best:
        rec = f"{best} offers the best combination of growth potential, manageable competition, and alignment with Cofilot's target demographic. Lower costs allow for faster break-even."
    elif "Vienna" in best:
        rec = f"{best} provides access to Vienna's established specialty coffee culture and affluent customer base, though higher investment is required."
    else:
        rec = f"{best} scores highest overall based on walkability, transit access, and coffee shop suitability metrics."

    return LocationComparison(
        locations=location_names,
        best_overall=best,
        comparison_factors=comparison,
        recommendation=rec,
    )
