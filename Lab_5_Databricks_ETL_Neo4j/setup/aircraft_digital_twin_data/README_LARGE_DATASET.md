# Aircraft Digital Twin Dataset - Large Scale Removal Records

## 🚨 **Important: Large Files Not Included in Git**

The large synthetic datasets (500K+ records, ~148MB total) are **not stored in git** due to GitHub's 100MB file size limit. You need to generate them locally using the provided script.

### **Quick Start - Generate Large Dataset**
```bash
cd aircraft_digital_twin_data
python3 generate_removal_data.py
```

This will create:
- `nodes_removals_large.csv` (~113MB)
- `rels_component_removal_large.csv` (~18MB)  
- `rels_aircraft_removal_large.csv` (~17MB)

## Overview
This directory contains a comprehensive aircraft digital twin dataset with large-scale removal records for aircraft maintenance analysis.

## Dataset Scale
- **Original dataset**: 60 removal records
- **Large dataset**: 500,000 removal records
- **Time span**: 2020-2024 (5 years)
- **Aircraft**: 20 aircraft with 320 components total

## Files

### Core Data Files (Original)
- `nodes_aircraft.csv` - 20 aircraft records
- `nodes_components.csv` - 320 component records  
- `nodes_systems.csv` - System hierarchy
- `nodes_maintenance.csv` - 300+ maintenance events
- `nodes_sensors.csv` - Sensor definitions
- `nodes_readings.csv` - Sensor readings data

### Large Scale Removal Dataset
- `nodes_removals_large.csv` - **500,000 removal records** (~113MB)
- `rels_component_removal_large.csv` - Component-removal relationships (~18MB)
- `rels_aircraft_removal_large.csv` - Aircraft-removal relationships (~17MB)

### Import Scripts
- `import.cypher` - Original import script for small dataset
- `import_large_dataset.cypher` - **Optimized import script for 500k records**
- `generate_removal_data.py` - Python script to generate large dataset

## Removal Data Schema

### Key Fields (RMV_TRK_NO, RMV_REA_TX)
- `RMV_TRK_NO` - Removal tracking number (e.g., "RMV230825000001")
- `RMV_REA_TX` - Detailed removal reason text
- `component_id` - Links to existing component structure
- `aircraft_id` - Links to existing aircraft structure

### Operational Metadata
- `removal_date` - When component was removed
- `installation_date` - When component was originally installed
- `work_order_number` - Maintenance work order
- `technician_id` - Technician who performed removal
- `part_number` & `serial_number` - Component identification

### Performance Metrics
- `time_since_install` - Hours between install and removal
- `flight_hours_at_removal` - Total flight hours when removed
- `flight_cycles_at_removal` - Total flight cycles when removed
- `cost_estimate` - Estimated cost of removal/replacement

### Business Logic
- `removal_priority` - CRITICAL, HIGH, MEDIUM, LOW
- `warranty_status` - IN_WARRANTY, OUT_WARRANTY
- `replacement_required` - Boolean flag
- `shop_visit_required` - Boolean flag  
- `scheduled_maintenance` - Boolean flag
- `removal_location` - Airport code where removal occurred
- `supplier_code` - Component supplier

## Data Generation Strategy

### Realistic Distributions
- **Removal reasons**: 60+ realistic failure modes with weighted distribution
  - Oil/lubrication issues (15%)
  - Bearing/mechanical wear (20%)  
  - Fuel system issues (18%)
  - Compressor/turbine issues (12%)
  - Electronic/sensor faults (10%)
  - Other categories (25%)

- **Priority levels**: Weighted by severity
  - CRITICAL (15%) - High cost, urgent
  - HIGH (35%) - Above average cost
  - MEDIUM (35%) - Average cost  
  - LOW (15%) - Below average cost, often scheduled

- **Warranty distribution**: 40% in-warranty, 60% out-of-warranty

### Performance Optimizations

#### Neo4j Import Optimizations
- Uses `CALL {} IN TRANSACTIONS` for large datasets
- Batches of 10,000 rows for removal data
- Proper indexing on key fields
- Constraint-based unique identification

#### Query Optimization Indexes
```cypher
CREATE INDEX FOR (r:RemovalEvent) ON (r.removal_date);
CREATE INDEX FOR (r:RemovalEvent) ON (r.aircraft_id);
CREATE INDEX FOR (r:RemovalEvent) ON (r.component_id);
CREATE INDEX FOR (r:RemovalEvent) ON (r.removal_priority);
CREATE INDEX FOR (r:RemovalEvent) ON (r.warranty_status);
CREATE INDEX FOR (r:RemovalEvent) ON (r.RMV_REA_TX);
```

## Sample Analytics Queries

The import script includes 10+ sample queries for:

1. **Cost Analysis**: Highest cost removals by reason, aircraft, supplier
2. **Reliability Analysis**: Mean time between removals (MTBR)
3. **Warranty Impact**: Cost differences between warranty status
4. **Seasonal Trends**: Monthly removal patterns
5. **Location Analysis**: Critical removals by airport
6. **Supplier Performance**: Part reliability by supplier
7. **Operational Impact**: Integration with flight delays and maintenance

## Usage

### Loading the Large Dataset
```bash
# Generate the large dataset (if not already done)
cd aircraft_digital_twin_data
python3 generate_removal_data.py

# Import into Neo4j using the optimized script
# Use import_large_dataset.cypher in Neo4j Browser or cypher-shell
```

### Memory Recommendations
- **Neo4j heap**: Minimum 4GB for 500k records
- **Page cache**: 2GB+ recommended  
- **Transaction batching**: Built into import script

### Expected Load Time
- **Small dataset** (original): 1-2 minutes
- **Large dataset** (500k): 15-30 minutes depending on hardware

## Data Quality Features

- **Referential integrity**: All component_id and aircraft_id values match existing data
- **Realistic temporal patterns**: Installation dates precede removal dates by 6 months to 3 years
- **Logical cost correlations**: Higher priority removals have higher costs
- **Geographic distribution**: Removals across 50+ airport codes
- **Supplier diversity**: 50 different suppliers with varying reliability patterns

## Use Cases

This large-scale dataset enables:

1. **Predictive maintenance modeling** with statistical significance
2. **Cost optimization analysis** across suppliers and components  
3. **Reliability engineering** with MTBR calculations
4. **Supply chain optimization** based on removal patterns
5. **Maintenance scheduling** optimization
6. **Digital twin simulations** with realistic historical data
7. **Machine learning training** for failure prediction models

## File Sizes
- `nodes_removals_large.csv`: ~113MB (500,001 lines)
- `rels_component_removal_large.csv`: ~18MB  
- `rels_aircraft_removal_large.csv`: ~17MB
- **Total dataset**: ~148MB of removal data

This provides a production-scale dataset suitable for enterprise digital twin analytics and maintenance optimization use cases.