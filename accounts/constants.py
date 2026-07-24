from django.db import models

# We agreed not to collect exact addresses or use location tracking, so pickups
# get coordinated at the general area level. Listings will reuse this list.


class CampusArea(models.TextChoices):
    NORTH_RESIDENTIAL = "north_residential", "North Residential Village"
    SOUTH_RESIDENTIAL = "south_residential", "South Residential Village"
    CASE_QUAD = "case_quad", "Case Quad"
    MATHER_QUAD = "mather_quad", "Mather Quad"
    HEALTH_CAMPUS = "health_campus", "Health Education Campus"
    UPTOWN = "uptown", "Uptown"
    LITTLE_ITALY = "little_italy", "Little Italy"
    COVENTRY = "coventry", "Coventry"
    OTHER_NEARBY = "other_nearby", "Other Nearby Area"
