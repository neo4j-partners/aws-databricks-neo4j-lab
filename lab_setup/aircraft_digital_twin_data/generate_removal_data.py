#!/usr/bin/env python3
"""
Generate large-scale aircraft removal records dataset (500,000 records)
Integrates with existing aircraft digital twin data structure
"""

import csv
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# Read existing aircraft and component data to maintain referential integrity
def read_aircraft_components(aircraft_file: str, components_file: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """Read aircraft IDs and component mappings from existing CSV files"""
    aircraft_ids = []
    aircraft_components = {}
    
    # Read aircraft
    with open(aircraft_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            aircraft_id = row[':ID(Aircraft)']
            aircraft_ids.append(aircraft_id)
            aircraft_components[aircraft_id] = []
    
    # Read components and map to aircraft
    with open(components_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            component_id = row[':ID(Component)']
            # Extract aircraft ID from component ID (format: AC1001-S01-C01)
            aircraft_id = component_id.split('-')[0]
            if aircraft_id in aircraft_components:
                aircraft_components[aircraft_id].append(component_id)
    
    return aircraft_ids, aircraft_components

# Removal reason categories with realistic distributions
REMOVAL_REASONS = [
    # Oil/Lubrication Issues (15%)
    "Oil leak detected during routine inspection",
    "Oil pressure regulating valve drift", 
    "Oil filter contamination beyond limits",
    "Oil cooler fan blade imbalance",
    "Oil scavenge pump impeller damage",
    "Oil tank quantity sensor erratic",
    "Accessory gearbox oil leak",
    
    # Bearing/Mechanical Wear (20%)
    "Bearing wear exceeds tolerance limits",
    "Bearing race cracking found during inspection",
    "Thrust bearing wear indicators triggered",
    "Bearing lubrication system blockage",
    "Engine mount bolt fatigue crack",
    "Accessory drive shaft vibration high",
    
    # Fuel System Issues (18%)
    "Fuel nozzle clogging reported by crew",
    "Fuel pump pressure irregularities", 
    "Fuel manifold cracking discovered",
    "Fuel control unit drift detected",
    "Fuel manifold pressure drop excessive",
    "Fuel pump bypass valve stuck closed",
    "Fuel injector spray pattern degraded",
    "Fuel metering unit calibration drift",
    "Main fuel filter differential pressure high",
    
    # Compressor/Turbine Issues (12%)
    "Compressor blade damage found during borescope",
    "Compressor stall during ground run",
    "Compressor inlet guide vane seizure",
    "Compressor discharge pressure sensor fault",
    "Compressor wash valve actuator stuck",
    "Compressor case drain leak",
    "Variable stator vane actuator binding",
    
    # Electronic/Sensor Faults (10%)
    "Electronic control unit fault codes present",
    "Speed sensor signal intermittent",
    "Engine oil temperature sensor drift",
    "Engine bleed air temperature sensor fault",
    "Variable geometry actuator position error",
    
    # Combustion System (8%)
    "Combustor liner burn through detected",
    "Combustor case thermal bowing",
    "Combustor drain valve stuck open",
    "Igniters electrode erosion excessive",
    
    # Vibration/Balance Issues (7%)
    "Vibration levels above acceptable threshold",
    "Fan blade tip damage from FOD",
    "Power turbine blade coating loss",
    "Gas generator turbine blade tip rubs",
    
    # Hydraulic/Pneumatic (5%)
    "Hydraulic actuator leakage detected",
    "Thrust reverser actuator malfunction",
    "Bleed air valve actuator failure",
    "Engine bleed air duct cracking",
    "Anti-ice valve actuator motor failure",
    
    # Scheduled/Calendar (3%)
    "Scheduled replacement due to calendar limit",
    "Scheduled overhaul interval reached",
    "Scheduled blade inspection interval reached",
    
    # Fire/Safety Systems (2%)
    "Engine fire detection loop chafing",
    "Engine fire extinguisher discharge valve leak",
    "Thrust reverser position feedback fault",
    "Engine mount shock strut leakage",
    "Starter cutout switch malfunction",
    "Starter motor brush wear limit reached",
    "Turbine clearance control valve failure",
    "Gearbox magnetic chip detector activation"
]

# Airport codes for removal locations
AIRPORT_CODES = [
    "LAX", "JFK", "ORD", "DFW", "ATL", "MIA", "SEA", "DEN", "PHX", "BOS",
    "IAH", "LAS", "MSP", "DTW", "CLT", "PDX", "SLC", "PHL", "TPA", "BWI",
    "MDW", "LGA", "SAN", "MCO", "EWR", "IAD", "HNL", "AUS", "BNA", "RDU",
    "MCI", "CLE", "MKE", "IND", "CVG", "PIT", "STL", "MSY", "OAK", "SJC",
    "SMF", "ABQ", "OKC", "TUL", "ELP", "SAT", "MEM", "JAX", "RSW", "PBI"
]

# Technician and supplier pools
TECHNICIANS = [f"TECH{i:03d}" for i in range(1, 201)]  # TECH001-TECH200
SUPPLIERS = [f"SUP{i:03d}" for i in range(1, 51)]      # SUP001-SUP050

def generate_part_number() -> str:
    """Generate realistic part number"""
    prefix = random.choice(['P', 'PN', 'PT'])
    number = random.randint(10000, 99999)
    suffix = random.randint(1, 999)
    return f"{prefix}{number}-{suffix:03d}"

def generate_serial_number() -> str:
    """Generate realistic serial number"""
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    numbers = random.randint(100000, 999999)
    return f"SN{letters}{numbers}"

def generate_work_order(date: datetime) -> str:
    """Generate work order number based on date"""
    year = date.year
    month = date.month
    day_of_year = date.timetuple().tm_yday
    sequence = random.randint(1, 999)
    return f"WO{year}-{month:02d}-{sequence:03d}"

def weighted_choice(choices: List[str], weights: List[float]) -> str:
    """Make a weighted random choice"""
    return random.choices(choices, weights=weights)[0]

def generate_removal_records(aircraft_components: Dict[str, List[str]], 
                           num_records: int = 500000,
                           start_date: datetime = datetime(2020, 1, 1),
                           end_date: datetime = datetime(2024, 12, 31)) -> List[Dict]:
    """Generate large-scale removal records"""
    
    records = []
    
    # Weight distributions for realistic data
    reason_weights = [0.15, 0.20, 0.18, 0.12, 0.10, 0.08, 0.07, 0.05, 0.03, 0.02]
    priority_weights = [0.15, 0.35, 0.35, 0.15]  # CRITICAL, HIGH, MEDIUM, LOW
    warranty_weights = [0.40, 0.60]  # IN_WARRANTY, OUT_WARRANTY
    
    priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    warranty_statuses = ["IN_WARRANTY", "OUT_WARRANTY"]
    
    print(f"Generating {num_records:,} removal records...")
    
    for i in range(num_records):
        if (i + 1) % 10000 == 0:
            print(f"Generated {i + 1:,} records...")
        
        # Select random aircraft and component
        aircraft_id = random.choice(list(aircraft_components.keys()))
        component_id = random.choice(aircraft_components[aircraft_id])
        
        # Generate random date within range
        time_delta = end_date - start_date
        random_days = random.randint(0, time_delta.days)
        removal_date = start_date + timedelta(days=random_days)
        
        # Installation date (6 months to 3 years before removal)
        install_days_back = random.randint(180, 1095)
        install_date = removal_date - timedelta(days=install_days_back)
        
        # Calculate time metrics
        time_since_install = install_days_back * 24  # Convert to hours
        flight_hours_at_removal = random.randint(1000, 25000)
        flight_cycles_at_removal = random.randint(200, 4000)
        
        # Select removal reason with realistic distribution
        reason_category_idx = random.choices(range(len(reason_weights)), weights=reason_weights)[0]
        reasons_in_category = len(REMOVAL_REASONS) // len(reason_weights)
        start_idx = reason_category_idx * reasons_in_category
        end_idx = min(start_idx + reasons_in_category, len(REMOVAL_REASONS))
        removal_reason = random.choice(REMOVAL_REASONS[start_idx:end_idx])
        
        # Generate other fields
        priority = weighted_choice(priorities, priority_weights)
        warranty_status = weighted_choice(warranty_statuses, warranty_weights)
        
        # Cost varies by priority and warranty
        base_cost = random.randint(2000, 50000)
        if priority == "CRITICAL":
            cost_multiplier = random.uniform(1.5, 3.0)
        elif priority == "HIGH":
            cost_multiplier = random.uniform(1.2, 2.0)
        elif priority == "MEDIUM":
            cost_multiplier = random.uniform(0.8, 1.5)
        else:  # LOW
            cost_multiplier = random.uniform(0.3, 1.0)
        
        cost_estimate = int(base_cost * cost_multiplier)
        
        # Scheduled maintenance is more common for LOW priority
        scheduled_maintenance = random.random() < (0.6 if priority == "LOW" else 0.1)
        
        record = {
            ":ID(RemovalEvent)": f"RE{i+1:06d}",
            "RMV_TRK_NO": f"RMV{removal_date.strftime('%y%m%d')}{i+1:06d}",
            "RMV_REA_TX": removal_reason,
            "component_id": component_id,
            "aircraft_id": aircraft_id,
            "removal_date": removal_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "work_order_number": generate_work_order(removal_date),
            "technician_id": random.choice(TECHNICIANS),
            "part_number": generate_part_number(),
            "serial_number": generate_serial_number(),
            "time_since_install": time_since_install,
            "flight_hours_at_removal": flight_hours_at_removal,
            "flight_cycles_at_removal": flight_cycles_at_removal,
            "replacement_required": random.random() < 0.85,  # 85% need replacement
            "shop_visit_required": random.random() < 0.60,   # 60% need shop visit
            "warranty_status": warranty_status,
            "removal_location": random.choice(AIRPORT_CODES),
            "scheduled_maintenance": scheduled_maintenance,
            "removal_priority": priority,
            "cost_estimate": cost_estimate,
            "supplier_code": random.choice(SUPPLIERS),
            "installation_date": install_date.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        records.append(record)
    
    return records

def write_csv(records: List[Dict], filename: str):
    """Write records to CSV file"""
    if not records:
        return
    
    fieldnames = list(records[0].keys())
    
    print(f"Writing {len(records):,} records to {filename}...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    print(f"Successfully wrote {filename}")

def generate_relationship_files(num_records: int, aircraft_components: Dict[str, List[str]]):
    """Generate relationship CSV files for component-removal and aircraft-removal"""
    
    print("Generating relationship files...")
    
    # Component-Removal relationships
    component_relations = []
    aircraft_relations = []
    
    for i in range(num_records):
        removal_id = f"RE{i+1:06d}"
        
        # Select random aircraft and component (same logic as main generation)
        aircraft_id = random.choice(list(aircraft_components.keys()))
        component_id = random.choice(aircraft_components[aircraft_id])
        
        component_relations.append({
            ":END_ID(RemovalEvent)": removal_id,
            ":START_ID(Component)": component_id,
            ":TYPE": "HAS_REMOVAL"
        })
        
        aircraft_relations.append({
            ":END_ID(RemovalEvent)": removal_id,
            ":START_ID(Aircraft)": aircraft_id,
            ":TYPE": "HAS_REMOVAL_EVENT"
        })
    
    # Write relationship files
    write_csv(component_relations, "rels_component_removal_large.csv")
    write_csv(aircraft_relations, "rels_aircraft_removal_large.csv")

def main():
    """Main execution function"""
    print("Starting large-scale aircraft removal data generation...")
    
    # Read existing data structure
    aircraft_ids, aircraft_components = read_aircraft_components(
        "nodes_aircraft.csv", 
        "nodes_components.csv"
    )
    
    print(f"Found {len(aircraft_ids)} aircraft with {sum(len(comps) for comps in aircraft_components.values())} components")
    
    # Generate removal records
    removal_records = generate_removal_records(
        aircraft_components, 
        num_records=500000,
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2024, 12, 31)
    )
    
    # Write main data file
    write_csv(removal_records, "nodes_removals_large.csv")
    
    # Generate relationship files
    generate_relationship_files(500000, aircraft_components)
    
    print("\nData generation complete!")
    print("Generated files:")
    print("- nodes_removals_large.csv (500,000 removal records)")
    print("- rels_component_removal_large.csv (500,000 component relationships)")
    print("- rels_aircraft_removal_large.csv (500,000 aircraft relationships)")

if __name__ == "__main__":
    main()