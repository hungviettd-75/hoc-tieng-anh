import os

learn_file_path = r"e:\Project\Hoc\hoc-tieng-anh\backend\app\api\v1\endpoints\learn.py"

# Mapping tat ca cac tu vung co so 2 sang cac tu dong nghia phu hop, chat luong
REPLACEMENTS = {
    '"Robot 2"': '"Android"',
    '"Smart 2"': '"Bright"',
    '"Data 2"': '"Information"',
    '"Code 2"': '"Syntax"',
    '"App 2"': '"Application"',
    '"User 2"': '"Operator"',
    '"Web 2"': '"Cyberspace"',
    '"Fast 2"': '"Rapid"',
    '"Computer 2"': '"Workstation"',
    '"System 2"': '"Mechanism"',
    '"Network 2"': '"Grid"',
    '"Program 2"': '"Utility"',
    '"Digital 2"': '"Cyber"',
    '"Device 2"': '"Gadget"',
    '"Storage 2"': '"Cache"',
    '"Process 2"': '"Procedure"',
    '"Automation 2"': '"Mechanization"',
    '"Database 2"': '"Repository"',
    '"Software 2"': '"Application"',
    '"Interface 2"': '"Console"',
    '"Assistant 2"': '"Aide"',
    '"Analyze 2"': '"Evaluate"',
    '"Prediction 2"': '"Projection"',
    '"Algorithm 2"': '"Formula"',
    '"Neural network 2"': '"Deep network"',
    '"Machine learning 2"': '"Pattern recognition"',
    '"Dataset 2"': '"Corpus"',
    '"Optimization 2"': '"Fine-tuning"',
    '"Classification 2"': '"Categorization"',
    '"Framework 2"': '"Infrastructure"',
    '"Generative 2"': '"Productive"',
    '"Autonomous 2"': '"Independent"',
    '"Cognitive computing 2"': '"Artificial brain"',
    '"Deep learning 2"': '"Neural computing"',
    '"Reinforcement 2"': '"Feedback loop"',
    '"Transformers 2"': '"Attention mechanism"',
    '"Supervised 2"': '"Guided learning"',
    '"Natural Language 2"': '"Speech recognition"',
    '"Hyperparameters 2"': '"Model parameters"',
    '"Backpropagation 2"': '"Gradient descent"',
    '"Destination 2"': '"Attraction"',
    '"Itinerary 2"': '"Schedule"',
    '"Accommodation 2"': '"Lodging"',
    '"Explore 2"': '"Discover"',
    '"Reservation 2"': '"Booking"',
    '"Adventure 2"': '"Journey"',
    '"Excursion 2"': '"Outing"',
    '"Passenger 2"': '"Traveler"',
    '"Ticket 2"': '"Pass"',
    '"Hotel 2"': '"Inn"',
    '"Bus 2"': '"Coach"',
    '"Map 2"': '"Guide"',
    '"Passport 2"': '"Visa"',
    '"Fly 2"': '"Travel"',
    '"Beach 2"': '"Coast"',
    '"Bag 2"': '"Luggage"',
    '"company 2"': '"enterprise"',
    '"trade 2"': '"commerce"',
    '"bank 2"': '"depository"',
    '"plan 2"': '"blueprint"',
    '"Destination 2"': '"Attraction"',
    '"Itinerary 2"': '"Schedule"',
    '"Accommodation 2"': '"Lodging"',
    '"Explore 2"': '"Discover"',
    '"Reservation 2"': '"Booking"',
    '"Adventure 2"': '"Journey"',
    '"Excursion 2"': '"Outing"',
    '"Passenger 2"': '"Traveler"',
    '"Ticket 2"': '"Pass"',
    '"Hotel 2"': '"Inn"',
    '"Bus 2"': '"Coach"',
    '"Map 2"': '"Guide"',
    '"Passport 2"': '"Visa"',
    '"Fly 2"': '"Travel"',
    '"Beach 2"': '"Coast"',
    '"Bag 2"': '"Luggage"',
}

# Them cac dang viet thuong khong viet hoa chu cai dau cho chac chan
REPLACEMENTS_LOWER = {k.lower(): v.lower() for k, v in REPLACEMENTS.items()}
ALL_REPLACEMENTS = {**REPLACEMENTS, **REPLACEMENTS_LOWER}

try:
    with open(learn_file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"File size before update: {len(content)} characters.")
    
    replace_count = 0
    for old, new in ALL_REPLACEMENTS.items():
        if old in content:
            content = content.replace(old, new)
            print(f"Replaced {old} -> {new}")
            replace_count += 1
            
    with open(learn_file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"File updated successfully! Total {replace_count} unique replacements made.")
except Exception as e:
    print("Error:", e)
