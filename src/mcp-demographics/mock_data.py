"""Mock data generator for Demographics.

Provides realistic demographic data for major European cities.
Uses curated data for known cities and seeded random generation for flexibility.
"""

import hashlib
import random
from typing import Dict, List, Optional

from models import (
    PopulationStats,
    IncomeDistribution,
    AgeDistribution,
    ConsumerSpending,
    LifestyleSegment,
    CommuterPattern,
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
# Curated City Data
# ============================================================================

CITY_DATA = {
    "vienna": {
        "population": 1_920_000,
        "density": 4_600,
        "growth_rate": 0.8,
        "median_age": 40.5,
        "median_income": 48_000,
        "mean_income": 55_000,
        "ppi": 115,  # Purchasing Power Index
        "unemployment": 8.5,
        "disposable_income": 28_000,
        "country": "austria",
        "coffee_culture": "traditional_strong",  # Strong café tradition, kaffeehauskultur
        "specialty_coffee_adoption": 0.35,  # 35% of coffee drinkers tried specialty
        "avg_coffee_spend_month": 85,  # EUR per capita monthly on coffee out-of-home
    },
    "prague": {
        "population": 1_350_000,
        "density": 2_700,
        "growth_rate": 1.2,
        "median_age": 42.1,
        "median_income": 22_000,  # EUR equivalent
        "mean_income": 26_000,
        "ppi": 95,
        "unemployment": 2.5,
        "disposable_income": 15_000,
        "country": "czech",
        "coffee_culture": "emerging_specialty",
        "specialty_coffee_adoption": 0.45,
        "avg_coffee_spend_month": 45,
    },
    "munich": {
        "population": 1_490_000,
        "density": 4_800,
        "growth_rate": 0.6,
        "median_age": 41.8,
        "median_income": 58_000,
        "mean_income": 68_000,
        "ppi": 140,
        "unemployment": 3.2,
        "disposable_income": 35_000,
        "country": "germany",
        "coffee_culture": "premium_mainstream",
        "specialty_coffee_adoption": 0.30,
        "avg_coffee_spend_month": 95,
    },
    "salzburg": {
        "population": 155_000,
        "density": 2_400,
        "growth_rate": 0.5,
        "median_age": 42.3,
        "median_income": 45_000,
        "mean_income": 52_000,
        "ppi": 108,
        "unemployment": 4.5,
        "disposable_income": 26_000,
        "country": "austria",
        "coffee_culture": "traditional_tourism",
        "specialty_coffee_adoption": 0.20,
        "avg_coffee_spend_month": 70,
    },
    "brno": {
        "population": 382_000,
        "density": 1_650,
        "growth_rate": 1.4,  # Growing tech hub
        "median_age": 38.5,  # Younger due to universities
        "median_income": 20_000,
        "mean_income": 24_000,
        "ppi": 88,
        "unemployment": 2.8,  # Lower than national average
        "disposable_income": 13_500,
        "country": "czech",
        "coffee_culture": "emerging_specialty",  # Strong third-wave movement
        "specialty_coffee_adoption": 0.52,  # Higher than Prague per capita
        "avg_coffee_spend_month": 38,  # Lower absolute but high relative to income
        "student_population": 65_000,  # 5 universities
        "tech_workers": 28_000,  # Growing IT sector
        "expat_population": 15_000,  # International community
    },
}

DISTRICT_MODIFIERS = {
    # Vienna districts - detailed for Cofilot expansion research
    "innere stadt": {"income_mult": 1.5, "density_mult": 1.2, "foot_traffic_mult": 3.0, "tourist_heavy": True, "rent_index": 2.5},
    "mariahilf": {"income_mult": 1.2, "density_mult": 1.3, "foot_traffic_mult": 2.5, "shopping": True, "hipster": True, "rent_index": 1.8},
    "neubau": {"income_mult": 1.25, "density_mult": 1.2, "foot_traffic_mult": 2.0, "hipster": True, "creative_class": True, "rent_index": 1.9},
    "leopoldstadt": {"income_mult": 1.0, "density_mult": 1.4, "foot_traffic_mult": 1.8, "diverse": True, "gentrifying": True, "rent_index": 1.4},
    "favoriten": {"income_mult": 0.8, "density_mult": 1.5, "foot_traffic_mult": 1.5, "working_class": True, "rent_index": 0.9},
    "josefstadt": {"income_mult": 1.3, "density_mult": 1.2, "foot_traffic_mult": 1.6, "upscale": True, "residential": True, "rent_index": 1.7},
    "wieden": {"income_mult": 1.15, "density_mult": 1.25, "foot_traffic_mult": 1.7, "mixed": True, "university": True, "rent_index": 1.5},
    "alsergrund": {"income_mult": 1.2, "density_mult": 1.3, "foot_traffic_mult": 1.9, "university": True, "medical_hub": True, "rent_index": 1.6},
    # Prague districts
    "prague 1": {"income_mult": 1.4, "density_mult": 1.0, "foot_traffic_mult": 4.0, "tourist_heavy": True, "rent_index": 3.0},
    "prague 2": {"income_mult": 1.3, "density_mult": 1.2, "foot_traffic_mult": 2.0, "residential": True, "rent_index": 2.2},
    "vinohrady": {"income_mult": 1.35, "density_mult": 1.1, "foot_traffic_mult": 1.8, "upscale": True, "expat_hub": True, "rent_index": 2.0},
    "žižkov": {"income_mult": 0.9, "density_mult": 1.4, "foot_traffic_mult": 1.5, "hipster": True, "gentrifying": True, "rent_index": 1.3},
    "karlín": {"income_mult": 1.25, "density_mult": 1.3, "foot_traffic_mult": 2.2, "tech_hub": True, "new_development": True, "rent_index": 1.8},
    "holešovice": {"income_mult": 1.1, "density_mult": 1.2, "foot_traffic_mult": 1.7, "creative_class": True, "galleries": True, "rent_index": 1.5},
    # Brno districts - key for Cofilot expansion analysis
    "brno-střed": {"income_mult": 1.3, "density_mult": 1.4, "foot_traffic_mult": 2.8, "city_center": True, "tourist_moderate": True, "rent_index": 1.8},
    "veveří": {"income_mult": 1.25, "density_mult": 1.3, "foot_traffic_mult": 2.2, "university": True, "student_hub": True, "tech_adjacent": True, "rent_index": 1.5},
    "královo pole": {"income_mult": 1.2, "density_mult": 1.2, "foot_traffic_mult": 1.8, "tech_hub": True, "university": True, "rent_index": 1.4},
    "židenice": {"income_mult": 0.95, "density_mult": 1.3, "foot_traffic_mult": 1.4, "residential": True, "gentrifying": True, "rent_index": 1.1},
    "černá pole": {"income_mult": 1.15, "density_mult": 1.1, "foot_traffic_mult": 1.5, "residential": True, "upscale": True, "rent_index": 1.3},
    "lesná": {"income_mult": 1.0, "density_mult": 1.4, "foot_traffic_mult": 1.2, "residential": True, "family_oriented": True, "rent_index": 1.0},
    "staré brno": {"income_mult": 1.1, "density_mult": 1.2, "foot_traffic_mult": 1.6, "historic": True, "student_hub": True, "rent_index": 1.2},
    # Munich districts
    "altstadt": {"income_mult": 1.6, "density_mult": 1.1, "foot_traffic_mult": 3.5, "tourist_heavy": True, "rent_index": 3.0},
    "maxvorstadt": {"income_mult": 1.3, "density_mult": 1.3, "foot_traffic_mult": 2.5, "university": True, "museum_district": True, "rent_index": 2.0},
    "schwabing": {"income_mult": 1.4, "density_mult": 1.2, "foot_traffic_mult": 2.0, "upscale": True, "creative_class": True, "rent_index": 2.2},
}

# Lifestyle segments common across cities
LIFESTYLE_SEGMENTS = [
    {
        "name": "Urban Professionals",
        "description": "Young professionals aged 25-40, career-focused, value convenience and quality",
        "percentage": 22,
        "characteristics": ["High disposable income", "Tech-savvy", "Time-poor", "Quality-conscious"],
        "coffee_index": 130,
        "channels": ["Premium cafés", "Mobile ordering", "Specialty coffee"],
        "price_sensitivity": "low",
    },
    {
        "name": "Students & Young Adults",
        "description": "University students and early career individuals, 18-28",
        "percentage": 18,
        "characteristics": ["Price-sensitive", "Social-oriented", "Digital natives", "Trend followers"],
        "coffee_index": 145,
        "channels": ["Budget-friendly cafés", "Study-friendly spaces", "Social media promotions"],
        "price_sensitivity": "high",
    },
    {
        "name": "Traditional Families",
        "description": "Families with children, value reliability and familiar brands",
        "percentage": 25,
        "characteristics": ["Quality-focused", "Brand loyal", "Weekend leisure", "Child-friendly preferences"],
        "coffee_index": 85,
        "channels": ["Established chains", "Family restaurants", "Weekend brunch spots"],
        "price_sensitivity": "medium",
    },
    {
        "name": "Coffee Enthusiasts",
        "description": "Specialty coffee lovers who seek unique experiences",
        "percentage": 8,
        "characteristics": ["Knowledge-seeking", "Experience-driven", "Will travel for good coffee", "Active on social media"],
        "coffee_index": 200,
        "channels": ["Third-wave cafés", "Roasteries", "Coffee workshops"],
        "price_sensitivity": "low",
    },
    {
        "name": "Senior Citizens",
        "description": "Retirees aged 65+, traditional preferences, regular routines",
        "percentage": 15,
        "characteristics": ["Routine-oriented", "Value service", "Traditional taste", "Newspaper readers"],
        "coffee_index": 70,
        "channels": ["Traditional cafés", "Neighborhood spots", "Bakery-cafés"],
        "price_sensitivity": "medium",
    },
    {
        "name": "Remote Workers",
        "description": "Work from anywhere professionals seeking workspace",
        "percentage": 12,
        "characteristics": ["Need WiFi & outlets", "Long dwell time", "Regular customers", "Laptop users"],
        "coffee_index": 160,
        "channels": ["Co-working cafés", "Quiet spots", "Good WiFi venues"],
        "price_sensitivity": "medium",
    },
]

SPENDING_CATEGORIES = {
    "food_beverage": {"name": "Food & Beverages", "avg_share": 14, "coffee_relevance": "high"},
    "dining_out": {"name": "Dining Out", "avg_share": 5, "coffee_relevance": "high"},
    "coffee": {"name": "Coffee (out of home)", "avg_share": 1.5, "coffee_relevance": "direct"},
    "entertainment": {"name": "Entertainment", "avg_share": 4, "coffee_relevance": "medium"},
    "retail": {"name": "Retail Shopping", "avg_share": 12, "coffee_relevance": "low"},
}


# ============================================================================
# Public API Functions
# ============================================================================


def _get_city_data(city: str) -> dict:
    """Get base city data, generating if not in curated set."""
    city_lower = city.lower().strip()

    # Check for direct match
    if city_lower in CITY_DATA:
        return CITY_DATA[city_lower]

    # Check for partial match
    for known_city, data in CITY_DATA.items():
        if known_city in city_lower or city_lower in known_city:
            return data

    # Generate for unknown city
    rng = _seeded_random(f"city-{city_lower}")
    return {
        "population": rng.randint(100_000, 800_000),
        "density": rng.randint(1500, 4000),
        "growth_rate": round(rng.uniform(-0.5, 2.0), 1),
        "median_age": round(rng.uniform(35, 45), 1),
        "median_income": rng.randint(25_000, 50_000),
        "mean_income": rng.randint(30_000, 60_000),
        "ppi": rng.randint(80, 120),
        "unemployment": round(rng.uniform(3, 10), 1),
        "disposable_income": rng.randint(15_000, 30_000),
        "country": "unknown",
    }


def _get_district_modifier(district: Optional[str]) -> dict:
    """Get modifier for a district."""
    if not district:
        return {"income_mult": 1.0, "density_mult": 1.0, "foot_traffic_mult": 1.0}

    district_lower = district.lower().strip()

    for known_district, mods in DISTRICT_MODIFIERS.items():
        if known_district in district_lower or district_lower in known_district:
            return mods

    # Generate for unknown district
    rng = _seeded_random(f"district-{district_lower}")
    return {
        "income_mult": round(rng.uniform(0.8, 1.3), 2),
        "density_mult": round(rng.uniform(0.8, 1.4), 2),
        "foot_traffic_mult": round(rng.uniform(0.8, 2.5), 2),
    }


def get_population_stats(
    city: str,
    district: Optional[str] = None,
) -> PopulationStats:
    """Get population statistics for a location."""
    city_data = _get_city_data(city)
    mod = _get_district_modifier(district)

    # Estimate district population as fraction of city
    district_pop_fraction = 0.08 if district else 1.0  # ~8% per district

    return PopulationStats(
        city=city.title(),
        district=district,
        total_population=int(city_data["population"] * district_pop_fraction) if district else city_data["population"],
        population_density_per_sqkm=city_data["density"] * mod.get("density_mult", 1.0),
        growth_rate_yoy=city_data["growth_rate"],
        median_age=city_data["median_age"],
        urban_percentage=100.0,
        data_year=2024,
    )


def get_income_distribution(
    city: str,
    district: Optional[str] = None,
) -> IncomeDistribution:
    """Get income and purchasing power data."""
    city_data = _get_city_data(city)
    mod = _get_district_modifier(district)
    income_mult = mod.get("income_mult", 1.0)

    median = city_data["median_income"] * income_mult
    mean = city_data["mean_income"] * income_mult

    return IncomeDistribution(
        city=city.title(),
        district=district,
        median_household_income=round(median, -2),
        mean_household_income=round(mean, -2),
        currency="EUR",
        purchasing_power_index=round(city_data["ppi"] * income_mult),
        income_brackets={
            "< €20,000": round(15 / income_mult, 1),
            "€20,000 - €40,000": 30.0,
            "€40,000 - €60,000": 25.0,
            "€60,000 - €80,000": round(15 * income_mult, 1),
            "€80,000 - €100,000": round(8 * income_mult, 1),
            "> €100,000": round(7 * income_mult, 1),
        },
        disposable_income_per_capita=round(city_data["disposable_income"] * income_mult, -2),
        unemployment_rate=city_data["unemployment"],
    )


def get_age_distribution(
    city: str,
    district: Optional[str] = None,
) -> AgeDistribution:
    """Get age demographics for a location."""
    city_data = _get_city_data(city)
    mod = _get_district_modifier(district)

    # Adjust age distribution based on district characteristics
    is_hipster = mod.get("hipster", False)
    is_university = mod.get("university", False)
    is_upscale = mod.get("upscale", False)

    base_groups = {
        "0-14": 13.0,
        "15-24": 11.0,
        "25-34": 16.0,
        "35-44": 15.0,
        "45-54": 14.0,
        "55-64": 13.0,
        "65+": 18.0,
    }

    if is_hipster or is_university:
        base_groups["15-24"] += 5
        base_groups["25-34"] += 5
        base_groups["65+"] -= 7
        base_groups["55-64"] -= 3

    if is_upscale:
        base_groups["35-44"] += 3
        base_groups["45-54"] += 3
        base_groups["15-24"] -= 4
        base_groups["0-14"] -= 2

    # Normalize to 100%
    total = sum(base_groups.values())
    age_groups = {k: round(v / total * 100, 1) for k, v in base_groups.items()}

    working_age = age_groups["15-24"] + age_groups["25-34"] + age_groups["35-44"] + age_groups["45-54"] + age_groups["55-64"]
    dependency = (age_groups["0-14"] + age_groups["65+"]) / working_age

    return AgeDistribution(
        city=city.title(),
        district=district,
        age_groups=age_groups,
        median_age=city_data["median_age"],
        dependency_ratio=round(dependency, 2),
        working_age_percentage=round(working_age, 1),
    )


def get_consumer_spending(
    city: str,
    category: str,
) -> ConsumerSpending:
    """Get consumer spending patterns by category."""
    city_data = _get_city_data(city)
    rng = _seeded_random(f"spending-{city}-{category}")

    category_lower = category.lower().replace(" ", "_")
    cat_info = SPENDING_CATEGORIES.get(category_lower, {
        "name": category.title(),
        "avg_share": 5,
        "coffee_relevance": "low",
    })

    # Calculate monthly spending based on disposable income and category share
    monthly_disposable = city_data["disposable_income"] / 12
    share = cat_info["avg_share"] + rng.uniform(-2, 2)
    monthly_avg = monthly_disposable * (share / 100)

    return ConsumerSpending(
        city=city.title(),
        category=cat_info["name"],
        monthly_average_per_household=round(monthly_avg, 0),
        currency="EUR",
        yoy_change=round(rng.uniform(-5, 10), 1),
        share_of_total_spending=round(share, 1),
        comparison_to_national=round(city_data["ppi"] + rng.randint(-10, 10)),
        seasonal_peak="December" if category_lower in ["retail", "entertainment"] else "Summer" if category_lower == "coffee" else None,
        notes=f"Based on {city.title()} consumer survey data 2024",
    )


def get_lifestyle_segments(
    city: str,
    district: Optional[str] = None,
) -> List[LifestyleSegment]:
    """Get consumer lifestyle segmentation."""
    mod = _get_district_modifier(district)
    rng = _seeded_random(f"segments-{city}-{district or 'city'}")

    results = []
    for seg in LIFESTYLE_SEGMENTS:
        # Adjust percentages based on district characteristics
        pct = seg["percentage"]

        if mod.get("hipster") and seg["name"] in ["Coffee Enthusiasts", "Students & Young Adults"]:
            pct *= 1.5
        if mod.get("university") and seg["name"] == "Students & Young Adults":
            pct *= 2.0
        if mod.get("upscale") and seg["name"] == "Urban Professionals":
            pct *= 1.4
        if mod.get("tech_hub") and seg["name"] == "Remote Workers":
            pct *= 1.8
        if mod.get("tourist_heavy") and seg["name"] == "Senior Citizens":
            pct *= 0.7  # Fewer locals

        # Add some randomness
        pct *= rng.uniform(0.9, 1.1)

        results.append(
            LifestyleSegment(
                segment_name=seg["name"],
                description=seg["description"],
                percentage_of_population=round(pct, 1),
                key_characteristics=seg["characteristics"],
                coffee_consumption_index=seg["coffee_index"],
                preferred_channels=seg["channels"],
                price_sensitivity=seg["price_sensitivity"],
            )
        )

    # Normalize to ~100%
    total = sum(r.percentage_of_population for r in results)
    for r in results:
        r.percentage_of_population = round(r.percentage_of_population / total * 100, 1)

    return results


def get_commuter_patterns(
    city: str,
    district: Optional[str] = None,
    day_type: str = "both",
) -> CommuterPattern:
    """Get commuter and foot traffic patterns."""
    city_data = _get_city_data(city)
    mod = _get_district_modifier(district)
    rng = _seeded_random(f"commuter-{city}-{district or 'city'}")

    foot_traffic_mult = mod.get("foot_traffic_mult", 1.0)

    # Base foot traffic on population density and district modifier
    base_traffic = city_data["density"] * 2  # Approximate daily pedestrians per sqkm
    daily_traffic = int(base_traffic * foot_traffic_mult * rng.uniform(0.9, 1.1))

    # Commuter flows
    is_center = mod.get("tourist_heavy") or mod.get("shopping")
    inflow = int(daily_traffic * (0.6 if is_center else 0.3))
    outflow = int(daily_traffic * (0.2 if is_center else 0.5))

    is_weekday = day_type.lower() in ["weekday", "both"]

    return CommuterPattern(
        city=city.title(),
        district=district,
        day_type="weekday" if day_type == "both" else day_type,
        peak_hours=["7:30-9:00", "12:00-13:00", "17:00-18:30"] if is_weekday else ["10:00-12:00", "14:00-17:00"],
        daily_foot_traffic=daily_traffic if is_weekday else int(daily_traffic * 0.7),
        commuter_inflow=inflow,
        commuter_outflow=outflow,
        public_transit_usage=round(rng.uniform(50, 75), 0),
        main_transit_modes=["Metro/U-Bahn", "Tram", "Bus"] if city_data.get("country") in ["austria", "germany"] else ["Metro", "Tram", "Bus"],
        average_commute_time_minutes=rng.randint(20, 40),
    )
