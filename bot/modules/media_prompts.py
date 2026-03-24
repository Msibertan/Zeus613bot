PROMPT_TRANSPORTER = """Scene
Early spring day at a European customs inspection zone.
Cool, fresh air with bright natural daylight and a sky with scattered clouds.
Dry worn asphalt with cracks, patched areas, and occasional shallow puddles typical for early spring road surfaces.

Background (secondary, partially visible only):
small guard booth
barrier gate
low-rise customs office building

Surface Condition — ALL VEHICLES (ABSOLUTE, NON-NEGOTIABLE)
Road dirt and salt:
clearly visible winter road grime typical after winter driving
gray-brown dried salt and dirt film on lower doors, sills, bumpers

License Plates & Frames (CRITICAL STRICT RULE)
ALL vehicles MUST have their license plates PHYSICALLY REMOVED.
Only an EMPTY, completely BLACK plastic mounting frame remains.

Transporter — Real European Autotransport (CRITICAL)
real European tractor + semi-trailer car transporter
two-level car carrier semi-trailer
Coupling logic (ABSOLUTE): fifth-wheel semi-trailer coupling only

Subject — HARD IDENTITY LOCK (NO SUBSTITUTIONS)
Primary vehicle must be IDENTICAL to the provided reference image.
"""

TRANSPORTER_ANGLES = [
    "Camera: eye-level. Angle: 3/4 view where the front side dominates, but the side of the car is still clearly visible.",
    "Camera: medium distance. Angle: 3/4 front view. The front fascia dominates the shot, but you can still clearly see the side profile.",
    "Camera: close proximity. Angle: front-dominant 3/4 perspective. The front of the vehicle is the main focus, while the side remains clearly in view."
]

PROMPT_CUSTOMS = """Scene: Ultra-realistic documentary smartphone photo of ONE EXACT vehicle from the provided reference image. HARD blueprint: absolute 1:1 identity lock, no substitutions, no interpretation.
Location: European customs impound yard, early spring conditions.
Subject — HARD IDENTITY LOCK (NO SUBSTITUTIONS)
Subject must be the EXACT SAME physical car as the reference image, part-for-part, with identical geometry, proportions, stance, paint color tone, front fascia, headlights, sensors, wheels, etc.

License Plate (CRITICAL STRICT RULE)
License plates MUST be physically removed from the vehicle. Only the factory empty black plastic mounting frame remains.

Environment
Industrial European customs impound yard in early spring: industrial buildings + guard booth, chain-link fence topped with barbed wire, orange barriers.

Ground (HARD)
NO snow anywhere. Winter-worn asphalt with dirty dried residue, grit, and compressed tire-track grime. NO clean asphalt. NO wet sheen. NO puddles.

Surface Condition (Real winter-driven)
Light winter road film across entire vehicle. NO stylize dirt/mud clumps.
Camera: STRICT 9:16 vertical portrait (native smartphone capture). Left-front 3/4 view with left headlight closest; front fascia dominates.
"""

PROMPT_EMPTY_PLATE = "The car has an empty black matte plastic license plate frame. The license plate is physically removed. No numbers, no text, no letters, no logos inside the frame. Visible mounting holes in the empty frame. Photorealistic, exact same car, identical background, perfectly preserved body geometry and original lighting."

BASE_STYLE = (
    "Amateur smartphone photography, candid social media post. "
    "STRICT RULES: 1) All people MUST look DIRECTLY at the camera lens, making eye contact. "
    "2) People must have demographics from Russia. "
    "3) If there are multiple people, they MUST wear completely DIFFERENT, mismatched clothing. No matching outfits. "
    "4) HARD CAR IDENTITY LOCK: The subject car must remain 1:1 identical to the reference image, part-for-part, zero modifications. "
    "5) Absolutely no text, no signs, no logos in the background."
)

REVIEW_PEOPLE = {
    'man_20': ["A young Russian man in his 20s", "A Slavic guy around 25 years old", "A young man looking happy with his car"],
    'man_30': ["A Russian man in his 30s", "A confident Slavic man around 35", "A typical Russian car owner in his 30s"],
    'man_40': ["A Russian man in his 40s", "A mature Slavic man", "An Eastern European man in his mid 40s"],
    'woman_20': ["A young Russian woman in her 20s", "A stylish Slavic girl around 25", "A happy young woman driver"],
    'woman_30': ["A Russian woman in her 30s", "A confident Slavic woman around 35", "An elegant Russian female car owner"],
    'woman_40': ["A mature Russian woman in her 40s", "A Slavic woman around 45", "A happy female driver in her 40s"],
    'couple_young': ["A young Russian couple (man and woman) in their 20s", "A happy young Slavic couple next to their car"],
    'couple_adult': ["A Russian couple in their 30s or 40s", "A mature Slavic husband and wife"],
    'family_1': ["A Russian family of three (man, woman, younger child)", "A happy young family with one kid"],
    'family_2': ["A Russian family of four (two parents, two kids)", "A large happy Slavic family"]
}

REVIEW_CLOTHES = [
    "wearing casual street clothes", "wearing a stylish jacket and jeans", "wearing business casual attire",
    "wearing a sporty outfit", "wearing a warm coat", "wearing everyday casual wear", "wearing a simple hoodie and jeans",
    "wearing fashionable European streetwear", "wearing a trendy casual outfit"
]

REVIEW_POSES = [
    "taking a selfie and looking directly at the camera lens",
    "leaning casually against the front hood, smiling and looking directly at the camera",
    "standing next to the driver's door, looking directly at the camera",
    "standing near the trunk, looking directly at the camera",
    "standing 1 meter away from the car, holding a coffee cup, looking directly at the camera",
    "standing in front of the car with crossed arms, looking directly at the camera",
    "leaning against the side of the car, looking directly at the camera",
    "sitting inside the car with the door open, looking directly out at the camera",
    "standing happily next to the car, looking directly at the camera"
]

REVIEW_LOCATIONS = {
    'city_center': ["A busy city street in a Russian metropolis", "Main avenue in a large Russian city with historic architecture", "City center with modern glass buildings in the background"],
    'residential_new': ["A quiet residential courtyard surrounded by modern new high-rise buildings", "New residential complex parking lot in Russia"],
    'residential_old': ["A classic Russian residential courtyard with old panel buildings (Khrushchyovka)", "A quiet older neighborhood yard in Russia with trees"],
    'industrial': ["An industrial zone with red brick buildings and warehouses in the background", "A rugged industrial factory background"],
    'business': ["A modern business center parking lot, tall glass office buildings in the background", "Corporate office district parking area"],
    'highway_forest': ["A narrow highway cutting through a dense pine forest", "A scenic forested road in Russia"],
    'highway_field': ["A wide highway running through vast open fields", "A straight country road with fields on both sides"],
    'gas_station': ["Near a modern Russian gas station with bright canopy lights", "A petrol station parking area"],
    'cafe': ["In front of a roadside cafe or fast-food drive-thru", "A coffee shop parking lot"],
    'mall': ["A large shopping mall parking lot facing the road, very few background cars", "An empty area of a modern retail mall parking lot"],
    'underground': ["An underground parking garage with concrete pillars and fluorescent lights", "A clean indoor parking lot with painted lines"],
    'park': ["Near the entrance of a large city park with tall trees", "A paved parking spot next to a green public park"],
    'waterfront': ["A city waterfront or river embankment with a nice view", "Parking along a concrete river walk"],
    'beach': ["A sandy or gravel parking area near a lake or beach", "Near a body of water in the countryside"],
    'mountain': ["A winding mountain road with scenic hilly backdrop", "A high-altitude viewpoint parking spot"],
    'dacha': ["In front of a typical Russian country 'dacha' house with a metal fence", "A gravel driveway of a modest suburban plot"],
    'cottage': ["In front of a wealthy suburban brick cottage with a nice gate", "A pristine paved driveway of an expensive private home"],
    'railway': ["Near a railway crossing with tracks in the background", "An industrial area with visible train tracks nearby"],
    'bridge': ["Under a large highway overpass or concrete bridge", "Next to a massive suspension bridge structure"],
    'square': ["A wide cobblestone town square with a monument in the distance", "A central plaza in a Russian town"]
}
