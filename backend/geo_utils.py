import re

# Comprehensive mapping of tech cities to their respective states/regions
CITY_TO_STATE = {
    # India - Kerala
    "kochi": "Kerala", "cochin": "Kerala", "trivandrum": "Kerala", "thiruvananthapuram": "Kerala",
    "kozhikode": "Kerala", "calicut": "Kerala", "thrissur": "Kerala", "palakkad": "Kerala",
    "alappuzha": "Kerala", "kollam": "Kerala", "kottayam": "Kerala", "kannur": "Kerala",
    "kasaragod": "Kerala", "ernakulam": "Kerala",
    
    # India - Other states
    "bangalore": "Karnataka", "bengaluru": "Karnataka", "mysore": "Karnataka", "mangalore": "Karnataka",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "hyderabad": "Telangana", "secunderabad": "Telangana",
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra",
    "delhi": "Delhi", "new delhi": "Delhi", "noida": "Uttar Pradesh", "gurgaon": "Haryana", "gurugram": "Haryana",
    "kolkata": "West Bengal", "calcutta": "West Bengal",
    
    # US - California
    "san francisco": "California", "los angeles": "California", "san diego": "California",
    "san jose": "California", "sacramento": "California", "palo alto": "California",
    "sunnyvale": "California", "mountain view": "California", "redwood city": "California",
    
    # US - Other States
    "new york": "New York", "new york city": "New York", "nyc": "New York", "albany": "New York",
    "austin": "Texas", "houston": "Texas", "dallas": "Texas", "fort worth": "Texas", "san antonio": "Texas",
    "seattle": "Washington", "redmond": "Washington", "bellevue": "Washington",
    "chicago": "Illinois", "boston": "Massachusetts", "cambridge": "Massachusetts",
    "atlanta": "Georgia", "miami": "Florida", "orlando": "Florida", "tampa": "Florida",
    
    # UK
    "london": "England", "manchester": "England", "birmingham": "England",
    "edinburgh": "Scotland", "glasgow": "Scotland", "cardiff": "Wales", "belfast": "Northern Ireland"
}

# Standard display names for recognized cities
CITY_DISPLAY_NAMES = {
    "kochi": "Kochi", "cochin": "Kochi", "trivandrum": "Trivandrum", "thiruvananthapuram": "Trivandrum",
    "kozhikode": "Kozhikode", "calicut": "Kozhikode", "thrissur": "Thrissur", "palakkad": "Palakkad",
    "alappuzha": "Alappuzha", "kollam": "Kollam", "kottayam": "Kottayam", "kannur": "Kannur",
    "kasaragod": "Kasaragod", "ernakulam": "Kochi",
    "bangalore": "Bangalore", "bengaluru": "Bangalore", "mysore": "Mysore", "mangalore": "Mangalore",
    "chennai": "Chennai", "coimbatore": "Coimbatore", "madurai": "Madurai",
    "hyderabad": "Hyderabad", "mumbai": "Mumbai", "pune": "Pune", "nagpur": "Nagpur",
    "delhi": "Delhi", "new delhi": "Delhi", "noida": "Noida", "gurgaon": "Gurgaon", "gurugram": "Gurgaon",
    "kolkata": "Kolkata", "calcutta": "Kolkata",
    "san francisco": "San Francisco", "los angeles": "Los Angeles", "san diego": "San Diego",
    "san jose": "San Jose", "sacramento": "Sacramento", "palo alto": "Palo Alto",
    "sunnyvale": "Sunnyvale", "mountain view": "Mountain View", "redwood city": "Redwood City",
    "new york": "New York", "new york city": "New York", "nyc": "New York",
    "austin": "Austin", "houston": "Houston", "dallas": "Dallas", "fort worth": "Dallas",
    "seattle": "Seattle", "redmond": "Redmond", "bellevue": "Bellevue",
    "chicago": "Chicago", "boston": "Boston", "cambridge": "Cambridge",
    "atlanta": "Atlanta", "miami": "Miami", "orlando": "Orlando", "tampa": "Tampa",
    "london": "London", "manchester": "Manchester", "birmingham": "Birmingham",
    "edinburgh": "Edinburgh", "glasgow": "Glasgow", "cardiff": "Cardiff", "belfast": "Belfast"
}

# Country code resolver for multi-region scrapers like Adzuna
COUNTRY_KEYWORDS = {
    "in": ["india", "kerala", "kochi", "trivandrum", "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad"],
    "gb": ["uk", "united kingdom", "great britain", "london", "manchester", "birmingham", "england", "scotland", "wales"],
    "us": ["usa", "united states", "america", "california", "texas", "new york", "seattle", "washington", "chicago", "boston"],
    "ca": ["canada", "toronto", "vancouver", "montreal", "ontario", "quebec", "alberta"],
    "au": ["australia", "sydney", "melbourne", "brisbane", "perth", "nsw", "victoria"],
    "nz": ["new zealand", "auckland", "wellington", "christchurch"],
    "de": ["germany", "deutschland", "berlin", "munich", "frankfurt", "hamburg"],
    "fr": ["france", "paris", "lyon", "marseille"],
    "nl": ["netherlands", "holland", "amsterdam", "rotterdam", "utrecht"],
    "sg": ["singapore"]
}

def resolve_country_code(location_or_region: str) -> str:
    """
    Parses location and extracts the matching country code. Defaults to 'us'.
    """
    if not location_or_region:
        return "us"
        
    loc_lower = location_or_region.lower()
    for code, keywords in COUNTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in loc_lower:
                return code
                
    return "us"

def get_state_from_city(location_str: str) -> str:
    """
    Identifies a known city in the location string and returns its mapped state/region.
    """
    if not location_str:
        return ""
        
    loc_lower = location_str.lower()
    for city, state in CITY_TO_STATE.items():
        # Word boundary match to avoid substring collision (e.g. 'noida' matching 'anoida')
        pattern = r'\b' + re.escape(city) + r'\b'
        if re.search(pattern, loc_lower):
            return state
            
    return ""

def get_standardized_city(location_str: str) -> str:
    """
    Identifies a city in the location string and returns its standard display name.
    """
    if not location_str:
        return ""
        
    loc_lower = location_str.lower()
    for city, display in CITY_DISPLAY_NAMES.items():
        pattern = r'\b' + re.escape(city) + r'\b'
        if re.search(pattern, loc_lower):
            return display
            
    return ""
