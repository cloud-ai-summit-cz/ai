"""Mock data generator for Government Data.

Provides realistic mock data for permits, zoning, regulations, and taxes.
Uses curated data for Austria, Czech Republic, and Germany with
seeded random generation for flexibility.
"""

import hashlib
import random
from typing import List, Optional

from models import (
    BusinessPermit,
    ZoningInfo,
    Regulation,
    TaxInfo,
    LicenseRequirement,
    HealthSafetyCode,
    LaborLaw,
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
# Curated Regulatory Data by Country
# ============================================================================

BUSINESS_PERMITS = {
    "at": [  # Austria
        {
            "id": "at-gewerbeschein",
            "name": "Gewerbeschein (Trade License)",
            "category": "general_business",
            "description": "General business license required for all commercial activities in Austria",
            "authority": "Bezirkshauptmannschaft / Magistrat",
            "cost": 150,
            "processing_days": 14,
            "validity_years": None,  # Unlimited
            "requirements": [
                "Proof of legal capacity",
                "No criminal record for relevant offenses",
                "Proof of professional qualification (if regulated trade)",
                "Business premises confirmation",
            ],
        },
        {
            "id": "at-gastgewerbe",
            "name": "Gastgewerbekonzession (Hospitality License)",
            "category": "food_service",
            "description": "Special license for restaurants, cafés, and food service establishments",
            "authority": "Bezirkshauptmannschaft / Magistrat",
            "cost": 350,
            "processing_days": 30,
            "validity_years": None,
            "requirements": [
                "Trade license (Gewerbeschein)",
                "Hygiene certification",
                "Fire safety approval",
                "Proof of suitable premises",
                "Certified training in food safety",
            ],
        },
        {
            "id": "at-betriebsanlage",
            "name": "Betriebsanlagengenehmigung (Operating Permit)",
            "category": "environment",
            "description": "Environmental and noise permit for business operations",
            "authority": "Bezirkshauptmannschaft",
            "cost": 500,
            "processing_days": 60,
            "validity_years": None,
            "requirements": [
                "Floor plans and technical drawings",
                "Environmental impact assessment",
                "Noise level measurements",
                "Waste disposal plan",
            ],
        },
    ],
    "cz": [  # Czech Republic
        {
            "id": "cz-zivnostensky",
            "name": "Živnostenský List (Trade License)",
            "category": "general_business",
            "description": "General trade license for business activities in Czech Republic",
            "authority": "Živnostenský úřad (Trade Licensing Office)",
            "cost": 1000,  # CZK, roughly 40 EUR
            "processing_days": 5,
            "validity_years": None,
            "requirements": [
                "Valid ID or passport",
                "Proof of legal capacity (18+ years)",
                "Clean criminal record",
                "Business premises confirmation",
            ],
        },
        {
            "id": "cz-stravovaci",
            "name": "Koncese pro stravovací služby (Food Service Concession)",
            "category": "food_service",
            "description": "Special concession for restaurants and food service",
            "authority": "Živnostenský úřad",
            "cost": 2000,  # CZK
            "processing_days": 30,
            "validity_years": None,
            "requirements": [
                "Trade license",
                "Professional qualification or 3 years experience",
                "Food hygiene certificate",
                "Health inspection approval",
            ],
        },
        {
            "id": "cz-hygienicka",
            "name": "Hygienická Stanice Approval",
            "category": "health",
            "description": "Health and hygiene approval for food establishments",
            "authority": "Krajská hygienická stanice",
            "cost": 500,  # CZK
            "processing_days": 21,
            "validity_years": 3,
            "requirements": [
                "HACCP plan",
                "Kitchen layout plans",
                "Water quality certification",
                "Staff health certifications",
            ],
        },
    ],
    "de": [  # Germany
        {
            "id": "de-gewerbeanmeldung",
            "name": "Gewerbeanmeldung (Business Registration)",
            "category": "general_business",
            "description": "Mandatory business registration with local authorities",
            "authority": "Gewerbeamt (Trade Office)",
            "cost": 60,
            "processing_days": 3,
            "validity_years": None,
            "requirements": [
                "Valid ID",
                "Business address confirmation",
                "Business activity description",
            ],
        },
        {
            "id": "de-gaststättenerlaubnis",
            "name": "Gaststättenerlaubnis (Restaurant License)",
            "category": "food_service",
            "description": "License to serve food and beverages to the public",
            "authority": "Ordnungsamt / Gewerbeamt",
            "cost": 500,
            "processing_days": 45,
            "validity_years": None,
            "requirements": [
                "Business registration",
                "Reliability certificate (Führungszeugnis)",
                "Health authority approval",
                "Fire safety certificate",
                "Proof of professional knowledge",
            ],
        },
        {
            "id": "de-gesundheitszeugnis",
            "name": "Gesundheitszeugnis (Health Certificate)",
            "category": "health",
            "description": "Health certificate required for food handlers",
            "authority": "Gesundheitsamt",
            "cost": 30,
            "processing_days": 7,
            "validity_years": None,
            "requirements": [
                "Attend hygiene training session",
                "Pass written test on food safety",
            ],
        },
    ],
}

ZONING_INFO = {
    "commercial_mixed": {
        "code": "MK",
        "name": "Mixed Commercial Zone",
        "description": "Areas designated for commercial and retail use with some residential",
        "permitted": ["Retail shops", "Restaurants", "Cafés", "Offices", "Services"],
        "prohibited": ["Heavy manufacturing", "Warehousing", "Industrial processing"],
        "max_height": 25,
        "far": 3.0,
        "noise": "Daytime: 60dB, Nighttime: 45dB",
        "hours": "6:00-22:00 for noise-generating activities",
        "outdoor": True,
        "signage": "Max 2sqm per facade, illuminated signs off by 22:00",
    },
    "city_center": {
        "code": "CC",
        "name": "City Center Zone",
        "description": "Historic city center with special preservation requirements",
        "permitted": ["Retail", "Restaurants", "Cultural venues", "Tourism services"],
        "prohibited": ["New construction over 4 floors", "Drive-through", "Large format retail"],
        "max_height": 18,
        "far": 2.5,
        "noise": "Daytime: 55dB, Nighttime: 40dB",
        "hours": "7:00-23:00 for food service, 24h with special permit",
        "outdoor": True,
        "signage": "Heritage-compatible only, no illuminated signs",
    },
    "residential_mixed": {
        "code": "WM",
        "name": "Mixed Residential Zone",
        "description": "Primarily residential with limited commercial ground floor use",
        "permitted": ["Small retail", "Cafés", "Services", "Medical offices"],
        "prohibited": ["Bars", "Nightclubs", "Large restaurants"],
        "max_height": 20,
        "far": 1.5,
        "noise": "Daytime: 50dB, Nighttime: 35dB",
        "hours": "8:00-20:00 for commercial",
        "outdoor": False,
        "signage": "Minimal, no illumination",
    },
}

TAX_RATES = {
    "at": [
        {"type": "Corporate Income Tax", "rate": 23.0, "rate_type": "percentage", "desc": "On company profits", "frequency": "annual"},
        {"type": "VAT (Food/Beverages)", "rate": 10.0, "rate_type": "percentage", "desc": "Reduced rate for food & non-alcoholic beverages", "frequency": "monthly"},
        {"type": "VAT (Standard)", "rate": 20.0, "rate_type": "percentage", "desc": "Standard rate for most goods/services", "frequency": "monthly"},
        {"type": "Municipal Business Tax", "rate": 3.0, "rate_type": "percentage", "desc": "Local business tax (Kommunalsteuer)", "frequency": "monthly"},
        {"type": "Social Security (Employer)", "rate": 21.83, "rate_type": "percentage", "desc": "Employer contribution to social security", "frequency": "monthly"},
    ],
    "cz": [
        {"type": "Corporate Income Tax", "rate": 21.0, "rate_type": "percentage", "desc": "On company profits", "frequency": "annual"},
        {"type": "VAT (Reduced)", "rate": 12.0, "rate_type": "percentage", "desc": "Reduced rate for food services", "frequency": "monthly"},
        {"type": "VAT (Standard)", "rate": 21.0, "rate_type": "percentage", "desc": "Standard rate", "frequency": "monthly"},
        {"type": "Social Security (Employer)", "rate": 33.8, "rate_type": "percentage", "desc": "Employer contributions", "frequency": "monthly"},
    ],
    "de": [
        {"type": "Corporate Income Tax", "rate": 15.0, "rate_type": "percentage", "desc": "Federal corporate tax", "frequency": "annual"},
        {"type": "Trade Tax", "rate": 14.0, "rate_type": "percentage", "desc": "Local trade tax (varies by municipality)", "frequency": "annual"},
        {"type": "VAT (Reduced)", "rate": 7.0, "rate_type": "percentage", "desc": "Reduced rate for takeaway food", "frequency": "monthly"},
        {"type": "VAT (Standard)", "rate": 19.0, "rate_type": "percentage", "desc": "Standard rate for dine-in", "frequency": "monthly"},
        {"type": "Social Security (Employer)", "rate": 19.975, "rate_type": "percentage", "desc": "Employer social contributions", "frequency": "monthly"},
    ],
}

LABOR_LAWS = {
    "at": [
        {"topic": "minimum_wage", "title": "Collective Agreement Minimum Wages", "desc": "Austria has no statutory minimum wage; wages set by sector collective agreements", "provisions": ["Hospitality sector: ~€1,800/month", "Annual increases negotiated", "13th and 14th month salary mandatory"]},
        {"topic": "working_hours", "title": "Working Hours Act (Arbeitszeitgesetz)", "desc": "Regulates maximum working hours and rest periods", "provisions": ["Max 8 hours/day, 40 hours/week standard", "Max 10 hours/day with compensation", "11 hours minimum rest between shifts", "35 hours weekly rest required"]},
        {"topic": "leave", "title": "Annual Leave Entitlement", "desc": "Minimum paid vacation and public holidays", "provisions": ["25 working days annual leave", "Increases to 30 days after 25 years", "13 public holidays", "Sick leave fully paid for 6 weeks"]},
    ],
    "cz": [
        {"topic": "minimum_wage", "title": "Statutory Minimum Wage", "desc": "Government-set minimum wage updated annually", "provisions": ["CZK 18,900/month (2024)", "CZK 112.50/hour", "Guaranteed wage supplements for difficult conditions"]},
        {"topic": "working_hours", "title": "Labour Code Working Time", "desc": "Maximum working hours regulations", "provisions": ["Max 40 hours/week", "Max 8 hours/day with exceptions", "30 minutes break after 6 hours", "11 hours rest between shifts"]},
        {"topic": "leave", "title": "Holiday Entitlement", "desc": "Paid leave requirements", "provisions": ["20 working days minimum annual leave", "13 public holidays", "Sick leave: 60% salary from day 15"]},
    ],
    "de": [
        {"topic": "minimum_wage", "title": "Mindestlohngesetz (Minimum Wage Act)", "desc": "Statutory minimum wage for all employees", "provisions": ["€12.41/hour (2024)", "Annual review by commission", "Applies to all sectors"]},
        {"topic": "working_hours", "title": "Arbeitszeitgesetz (Working Hours Act)", "desc": "Limits on working time", "provisions": ["Max 8 hours/day, 48 hours/week", "Can extend to 10 hours if averaged", "11 hours minimum rest", "Sundays and public holidays protected"]},
        {"topic": "leave", "title": "Bundesurlaubsgesetz (Federal Leave Act)", "desc": "Minimum paid vacation", "provisions": ["24 working days minimum (6-day week basis)", "20 days for 5-day week", "9-13 public holidays by state", "Continued pay during illness for 6 weeks"]},
    ],
}


# ============================================================================
# Public API Functions
# ============================================================================


def get_country_code(city: str, country: Optional[str] = None) -> str:
    """Determine country code from city or country name."""
    text = f"{city} {country or ''}".lower()

    if any(x in text for x in ["vienna", "wien", "austria", "österreich", "at", "salzburg", "graz", "innsbruck"]):
        return "at"
    if any(x in text for x in ["prague", "praha", "czech", "brno", "ostrava", "cz"]):
        return "cz"
    if any(x in text for x in ["munich", "münchen", "berlin", "hamburg", "frankfurt", "germany", "deutschland", "de"]):
        return "de"

    # Default to Austria for unknown
    return "at"


def get_business_permits(
    city: str,
    business_type: str,
    country: Optional[str] = None,
) -> List[BusinessPermit]:
    """Get required permits for a business type in a location."""
    country_code = get_country_code(city, country)
    permits_data = BUSINESS_PERMITS.get(country_code, BUSINESS_PERMITS["at"])

    results = []
    for p in permits_data:
        # Include all permits - they're all typically required for food service
        if business_type.lower() in ["coffee_shop", "cafe", "café", "restaurant", "food"]:
            results.append(
                BusinessPermit(
                    permit_id=p["id"],
                    name=p["name"],
                    category=p["category"],
                    description=p["description"],
                    issuing_authority=p["authority"],
                    estimated_cost=p["cost"],
                    processing_time_days=p["processing_days"],
                    validity_years=p.get("validity_years"),
                    requirements=p["requirements"],
                )
            )
        elif p["category"] == "general_business":
            # Always include general business license
            results.append(
                BusinessPermit(
                    permit_id=p["id"],
                    name=p["name"],
                    category=p["category"],
                    description=p["description"],
                    issuing_authority=p["authority"],
                    estimated_cost=p["cost"],
                    processing_time_days=p["processing_days"],
                    validity_years=p.get("validity_years"),
                    requirements=p["requirements"],
                )
            )

    return results


def get_zoning_info(
    city: str,
    district: Optional[str] = None,
    address: Optional[str] = None,
) -> ZoningInfo:
    """Get zoning information for a location."""
    # Determine zone type based on district hints
    district_lower = (district or "").lower()
    address_lower = (address or "").lower()
    combined = f"{district_lower} {address_lower}"

    if any(x in combined for x in ["center", "zentrum", "altstadt", "old town", "innere", "historic"]):
        zone = ZONING_INFO["city_center"]
    elif any(x in combined for x in ["residential", "wohn", "suburb"]):
        zone = ZONING_INFO["residential_mixed"]
    else:
        zone = ZONING_INFO["commercial_mixed"]

    return ZoningInfo(
        zone_code=zone["code"],
        zone_name=zone["name"],
        description=zone["description"],
        permitted_uses=zone["permitted"],
        prohibited_uses=zone["prohibited"],
        max_building_height_m=zone["max_height"],
        max_floor_area_ratio=zone["far"],
        noise_restrictions=zone["noise"],
        operating_hours_restrictions=zone["hours"],
        outdoor_seating_allowed=zone["outdoor"],
        signage_restrictions=zone["signage"],
    )


def get_regulations(
    country: str,
    industry: str,
    category: Optional[str] = None,
) -> List[Regulation]:
    """Get industry-specific regulations."""
    country_code = get_country_code("", country)

    results = []
    rng = _seeded_random(f"reg-{country_code}-{industry}")

    # Generate relevant regulations
    reg_templates = [
        ("Food Safety Act", "health", "Comprehensive food safety requirements for establishments serving food"),
        ("Fire Safety Regulations", "safety", "Fire prevention and safety requirements for commercial premises"),
        ("Employment Protection Act", "employment", "Worker rights and employer obligations"),
        ("Environmental Health Standards", "environment", "Environmental standards for food service operations"),
        ("Accessibility Requirements", "safety", "Requirements for disabled access in public establishments"),
    ]

    for title, cat, desc in reg_templates:
        if category and category != "all" and cat != category:
            continue

        results.append(
            Regulation(
                regulation_id=f"reg-{country_code}-{title.lower().replace(' ', '-')[:20]}",
                title=title,
                category=cat,
                description=desc,
                authority=f"Ministry of {cat.title()}",
                key_requirements=[
                    f"Requirement {i+1} for {title}"
                    for i in range(rng.randint(2, 5))
                ],
            )
        )

    return results


def get_tax_rates(
    country: str,
    city: Optional[str] = None,
    business_type: Optional[str] = None,
) -> List[TaxInfo]:
    """Get business tax rates for a location."""
    country_code = get_country_code(city or "", country)
    taxes = TAX_RATES.get(country_code, TAX_RATES["at"])

    results = []
    for t in taxes:
        results.append(
            TaxInfo(
                tax_type=t["type"],
                rate=t["rate"],
                rate_type=t["rate_type"],
                description=t["desc"],
                filing_frequency=t["frequency"],
            )
        )

    return results


def get_licensing_requirements(
    country: str,
    profession: str,
) -> List[LicenseRequirement]:
    """Get professional licensing requirements."""
    country_code = get_country_code("", country)
    rng = _seeded_random(f"license-{country_code}-{profession}")

    results = []

    # Food handler certification is always required
    if profession.lower() in ["food_handler", "barista", "cook", "chef", "server"]:
        results.append(
            LicenseRequirement(
                license_id=f"lic-{country_code}-food-handler",
                name="Food Handler Certificate",
                profession="food_handler",
                description="Certification demonstrating knowledge of food safety and hygiene practices",
                issuing_authority="Health Authority",
                requirements=[
                    "Complete food safety training course",
                    "Pass written examination",
                    "Valid health certificate",
                ],
                training_hours_required=8,
                exam_required=True,
                renewal_period_years=3,
                estimated_cost=50 if country_code != "cz" else 800,  # CZK for CZ
            )
        )

    # Barista certification (optional but recommended)
    if profession.lower() in ["barista", "coffee"]:
        results.append(
            LicenseRequirement(
                license_id=f"lic-{country_code}-barista",
                name="Professional Barista Certification",
                profession="barista",
                description="Optional certification demonstrating coffee preparation expertise",
                issuing_authority="SCA (Specialty Coffee Association)",
                requirements=[
                    "Complete SCA Barista Skills course",
                    "Practical skills demonstration",
                    "Written theory exam",
                ],
                training_hours_required=16,
                exam_required=True,
                renewal_period_years=5,
                estimated_cost=300,
            )
        )

    return results


def get_health_safety_codes(
    country: str,
    establishment_type: str,
) -> List[HealthSafetyCode]:
    """Get health and safety codes for an establishment type."""
    country_code = get_country_code("", country)

    results = [
        HealthSafetyCode(
            code_id=f"hsc-{country_code}-food-safety",
            title="Food Safety Standards",
            category="food_safety",
            description="HACCP-based food safety requirements for food service establishments",
            key_requirements=[
                "Implement HACCP food safety management system",
                "Maintain food temperature logs",
                "Separate raw and cooked food preparation areas",
                "Regular cleaning and sanitation schedules",
                "Staff food hygiene training",
                "Pest control program",
            ],
            inspection_frequency="Annual, with random spot checks",
            penalties="Fines €500-€50,000, closure for serious violations",
        ),
        HealthSafetyCode(
            code_id=f"hsc-{country_code}-fire-safety",
            title="Fire Safety Requirements",
            category="fire_safety",
            description="Fire prevention and evacuation requirements",
            key_requirements=[
                "Fire extinguishers at designated locations",
                "Emergency exit signs and lighting",
                "Fire detection and alarm system",
                "Annual fire safety inspection",
                "Staff fire safety training",
                "Evacuation plan posted",
            ],
            inspection_frequency="Annual",
            penalties="Fines up to €25,000, closure for non-compliance",
        ),
        HealthSafetyCode(
            code_id=f"hsc-{country_code}-workplace",
            title="Workplace Safety Standards",
            category="workplace_safety",
            description="Occupational health and safety requirements",
            key_requirements=[
                "Risk assessment documentation",
                "Personal protective equipment where required",
                "First aid kit and trained first aider",
                "Safe equipment operation procedures",
                "Accident reporting system",
            ],
            inspection_frequency="Biennial",
        ),
        HealthSafetyCode(
            code_id=f"hsc-{country_code}-accessibility",
            title="Accessibility Standards",
            category="accessibility",
            description="Requirements for disabled access and accommodation",
            key_requirements=[
                "Step-free entrance or ramp",
                "Accessible toilet facilities",
                "Adequate circulation space",
                "Clear signage",
            ],
            inspection_frequency="Initial approval and major renovations",
        ),
    ]

    return results


def get_labor_laws(
    country: str,
    topics: Optional[List[str]] = None,
) -> List[LaborLaw]:
    """Get employment and labor regulations."""
    country_code = get_country_code("", country)
    laws = LABOR_LAWS.get(country_code, LABOR_LAWS["at"])

    results = []
    for law in laws:
        if topics and law["topic"] not in topics:
            continue

        results.append(
            LaborLaw(
                law_id=f"law-{country_code}-{law['topic']}",
                topic=law["topic"],
                title=law["title"],
                description=law["desc"],
                key_provisions=law["provisions"],
            )
        )

    # If no specific topics, return all
    if not topics:
        return results

    return results
