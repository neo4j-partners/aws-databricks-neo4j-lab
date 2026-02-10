# A321neo Maintenance and Troubleshooting Manual

**Document Number:** AMM-A321neo-2024-001
**Revision:** 1.0
**Effective Date:** October 1, 2024
**Applicability:** A321neo series aircraft equipped with CFM LEAP-1A engines
**Operator:** RegionalCo
**Fleet:** N54980C, N86057G, N89365K, N65164O, N96107S

---

## Document Control

| Rev | Date | Description | Author |
|-----|------|-------------|--------|
| 1.0 | 2024-10-01 | Initial Release | Engineering Division |
| 0.9 | 2024-09-15 | Draft for review | Maintenance Planning |

**NOTICE:** This manual contains proprietary information. Maintenance procedures must be performed by certified personnel only. Always refer to the latest revision of Airbus AMM documentation for authoritative guidance.

---

## Table of Contents

1. [Aircraft Overview](#1-aircraft-overview)
2. [System Architecture](#2-system-architecture)
3. [Engine System - LEAP-1A](#3-engine-system---leap-1a)
4. [Engine Troubleshooting Procedures](#4-engine-troubleshooting-procedures)
5. [Avionics System](#5-avionics-system)
6. [Hydraulics System](#6-hydraulics-system)
7. [Fault Code Reference](#7-fault-code-reference)
8. [Troubleshooting Decision Trees](#8-troubleshooting-decision-trees)
9. [Scheduled Maintenance Tasks](#9-scheduled-maintenance-tasks)
10. [Appendices](#10-appendices)

---

## 1. Aircraft Overview

### 1.1 General Specifications

| Parameter | Value |
|-----------|-------|
| Aircraft Type | Airbus A321-271N (A321neo) |
| Powerplant | 2x CFM International LEAP-1A32 Turbofan |
| Maximum Takeoff Weight (MTOW) | 97,000 kg (213,848 lb) |
| Maximum Landing Weight (MLW) | 79,200 kg (174,606 lb) |
| Maximum Zero Fuel Weight (MZFW) | 73,300 kg (161,601 lb) |
| Fuel Capacity | 32,940 liters (8,703 US gal) |
| Range | 7,400 km (4,000 nm) |
| Service Ceiling | 39,800 ft |
| Cruise Speed | Mach 0.78 (450 ktas) |
| Passengers (Typical) | 180-220 |

### 1.2 A321neo "New Engine Option" Features

The A321neo represents the latest evolution of the A320 family with:

- **15% fuel burn reduction** compared to previous generation
- **CFM LEAP-1A engines** with advanced 3D woven carbon fiber fan blades
- **Sharklet wingtips** (2.4m height) reducing drag by 4%
- **New cabin design** with wider overhead bins
- **Fly-by-wire flight controls** with enhanced envelope protection
- **Advanced avionics** with improved FMS capabilities

### 1.3 Fleet Configuration

The RegionalCo A321neo fleet consists of five aircraft configured for medium to long-haul operations:

| Aircraft ID | Registration | ICAO 24 | Entry into Service |
|-------------|--------------|---------|-------------------|
| AC1003 | N54980C | 6d4e29 | March 2021 |
| AC1007 | N86057G | b3f182 | July 2021 |
| AC1011 | N89365K | e8a4c6 | November 2021 |
| AC1015 | N65164O | 4c7d91 | March 2022 |
| AC1019 | N96107S | 91b5f3 | July 2022 |

### 1.4 ATA Chapter Reference

This manual covers the following ATA chapters:

| ATA Chapter | System | Reference Section |
|-------------|--------|-------------------|
| ATA 29 | Hydraulic Power | Section 6 |
| ATA 34 | Navigation | Section 5 |
| ATA 71 | Powerplant | Sections 3-4 |
| ATA 72 | Engine | Sections 3-4 |
| ATA 73 | Engine Fuel and Control | Section 3 |
| ATA 77 | Engine Indicating | Section 3 |
| ATA 79 | Oil | Section 3 |

---

## 2. System Architecture

### 2.1 Major System Groups

Each A321neo aircraft comprises four primary monitored system groups:

```
AIRCRAFT (A321neo)
│
├── ENGINE SYSTEM #1 (LEAP-1A Left)
│   ├── Fan Module (Carbon Fiber Composite)
│   ├── Compressor Stage (High-Pressure)
│   ├── High-Pressure Turbine
│   ├── Main Fuel Pump
│   └── Thrust Bearing Assembly
│
├── ENGINE SYSTEM #2 (LEAP-1A Right)
│   ├── Fan Module (Carbon Fiber Composite)
│   ├── Compressor Stage (High-Pressure)
│   ├── High-Pressure Turbine
│   ├── Main Fuel Pump
│   └── Thrust Bearing Assembly
│
├── AVIONICS SYSTEM
│   ├── Flight Management System (FMS)
│   ├── Air Data Computer (ADC)
│   └── Navigation Receiver (NAV)
│
└── HYDRAULICS SYSTEM
    ├── Main Hydraulic Pump
    ├── Hydraulic Reservoir
    └── Flap Actuator Assembly
```

#### 2.1.1 Engine Systems (LEAP-1A)

The A321neo is powered by two CFM International LEAP-1A high-bypass turbofan engines, representing the most significant advancement in narrow-body propulsion in decades. Each engine produces up to 32,900 lbf of thrust and delivers 15% better fuel efficiency than previous generation engines. The LEAP-1A features revolutionary 3D woven carbon fiber composite fan blades—a first for commercial aviation—reducing weight while improving durability and foreign object damage resistance. The engine incorporates a twin-annular, pre-mixing swirler (TAPS II) combustor for reduced NOx emissions, ceramic matrix composite (CMC) shrouds in the high-pressure turbine, and an advanced active clearance control system. Engine health monitoring via the FADEC provides real-time data on exhaust gas temperature (EGT), vibration, fan speed (N1), and fuel flow, with enhanced diagnostic capabilities through the Engine Monitoring Unit (EMU). The engine systems account for approximately 61% of all maintenance events in the fleet, with vibration exceedance and contamination being the most prevalent issues—characteristic of new technology adoption.

**ATA Reference:** Chapters 71 (Powerplant), 72 (Engine), 73 (Engine Fuel and Control), 77 (Engine Indicating), 79 (Oil)

#### 2.1.2 Avionics System

The A321neo features the latest Airbus avionics suite built on enhanced fly-by-wire architecture with improved system integration. The system centers on dual Flight Management Systems (FMS) providing Required Navigation Performance (RNP) 0.1 capability, enabling precision approaches without ground-based navigation aids. Three Air Data and Inertial Reference Units (ADIRU) provide redundant altitude, airspeed, attitude, and position data through integrated air data modules and laser ring gyroscopes. The Multi-Mode Receiver (MMR) integrates VOR/ILS, GPS (L1/L5), SBAS, and GBAS capabilities for worldwide navigation. The cockpit features six LCD displays with enhanced vision system (EVS) compatibility. All avionics communicate via AFDX (Avionics Full-Duplex Switched Ethernet) data network with comprehensive Built-In Test Equipment (BITE). Avionics-related maintenance events comprise approximately 20% of fleet issues, with electrical faults and sensor drift being the primary concerns addressed through software patches and calibration.

**ATA Reference:** Chapter 34 (Navigation)

#### 2.1.3 Hydraulics System

The A321neo hydraulic system provides power for flight control surfaces, slats/flaps, landing gear, wheel brakes, thrust reversers, and cargo doors. The aircraft employs three independent hydraulic systems designated Green, Blue, and Yellow, each operating at 3,000 psi with enhanced redundancy compared to earlier A320 variants. The Green system is powered by an engine-driven pump on Engine #1, the Yellow system by Engine #2, and the Blue system by an electric pump with RAT (Ram Air Turbine) backup. Each system includes variable-displacement pumps capable of 34 gpm flow rate, a pressurized reservoir with bootstrap design, and multiple actuators including the flap Power Control Unit (PCU). Hydraulic fluid (Skydrol LD-4 or HyJet V) requires regular monitoring for contamination and proper levels. The hydraulics system represents approximately 19% of maintenance events, with leaks and contamination being the primary concerns, consistent with fleet maturity.

**ATA Reference:** Chapter 29 (Hydraulic Power)

### 2.2 Engine Health Monitoring

Each LEAP-1A engine is equipped with comprehensive monitoring sensors:

| Sensor Type | Parameter | Unit | Location |
|-------------|-----------|------|----------|
| EGT | Exhaust Gas Temperature | °C | HPT exit (8 thermocouples) |
| VIB | Engine Vibration | ips (inches/sec) | Fan case, core case |
| N1Speed | Fan Speed | % RPM | Fan shaft |
| N2 | Core Speed | % RPM | HP shaft |
| FuelFlow | Fuel Flow | kg/s | Fuel metering unit |
| OIL-P | Oil Pressure | psi | Main oil gallery |
| OIL-T | Oil Temperature | °C | Scavenge return |
| OIL-Q | Oil Quantity | % | Oil tank |

**Sensor Sampling Rate:** Continuous (1 Hz flight data, 50 Hz vibration analysis)

**Engine Monitoring Unit (EMU):** The LEAP-1A features an enhanced EMU providing:
- Real-time trend monitoring
- Automated fault detection and isolation
- Prognostic health management
- Wireless ground data transmission capability

### 2.3 Component Identification Schema

Components are identified using the following nomenclature:

```
[Aircraft ID]-[System]-[Component]

Example: AC1003-S01-C01
         │       │    └── Component: Fan Module
         │       └─────── System: Engine #1
         └─────────────── Aircraft: AC1003 (N54980C)
```

**System Codes:**
- S01: Engine #1 (Left)
- S02: Engine #2 (Right)
- S03: Avionics Suite
- S04: Hydraulics System

---

## 3. Engine System - LEAP-1A

### 3.1 Engine Specifications

| Parameter | Value |
|-----------|-------|
| Manufacturer | CFM International (GE/Safran) |
| Model | LEAP-1A32 |
| Type | Two-spool, high-bypass turbofan |
| Thrust Rating | 32,900 lbf (146 kN) |
| Bypass Ratio | 11:1 |
| Overall Pressure Ratio | 40:1 |
| Dry Weight | 2,990 kg (6,592 lb) |
| Fan Diameter | 1.98 m (78 inches) |
| Length | 3.34 m (131.5 inches) |
| Fan Blades | 18 (3D woven carbon fiber composite) |

### 3.2 LEAP-1A Technology Highlights

The LEAP-1A incorporates several breakthrough technologies:

**Carbon Fiber Fan Blades:**
- 3D woven resin transfer molded (RTM) construction
- 500 lbs lighter than equivalent titanium fan
- Superior FOD resistance with self-healing matrix
- Reduced maintenance costs (no blend repairs)

**Ceramic Matrix Composites (CMC):**
- HPT shrouds made from silicon carbide CMC
- 1/3 the weight of metal equivalents
- Higher temperature capability (+200°F)
- Reduced cooling air requirements

**TAPS II Combustor:**
- Twin Annular Premixing Swirler design
- 50% reduction in NOx emissions
- Improved pattern factor for HPT life
- Better altitude relight capability

**Active Clearance Control:**
- Real-time blade tip clearance management
- Improved specific fuel consumption
- Reduced EGT margin deterioration

### 3.3 Component Descriptions

#### 3.3.1 Fan Module
**Part Number:** LEAP-FM-1A32-100
**ATA Reference:** 72-21

The fan module features 18 wide-chord 3D woven carbon fiber composite blades—a revolutionary technology exclusive to LEAP engines. Each blade is manufactured using Resin Transfer Molding (RTM) with a titanium leading edge for erosion protection.

**Key Characteristics:**
- Blade weight: 11.3 kg (vs. 25 kg for titanium)
- Tip speed: 1,570 ft/sec at takeoff
- Containment: Kevlar fan case with ballistic protection

**Inspection Intervals:**
- Visual inspection: Every 750 flight hours
- Detailed inspection: Every 5,000 flight hours
- Blade replacement: On-condition only (no life limit)

**Composite Blade Damage Assessment:**
Unlike metal blades, composite fan blades require specialized inspection:

| Damage Type | Acceptable Limit | Action Required |
|-------------|-----------------|-----------------|
| Leading edge nick | < 3mm depth | Monitor |
| Delamination | None visible | Replace blade |
| Matrix cracking | Surface only, < 25mm | Repair per SRM |
| Impact damage | Per CFM assessment | Engineering review |

#### 3.3.2 Compressor Stage (High-Pressure)
**Part Number:** LEAP-HPC-1A32-200
**ATA Reference:** 72-32

The 10-stage high-pressure compressor achieves a pressure ratio of 22:1, significantly higher than previous generation engines. Stages 1-5 feature variable stator vanes (VSV) with improved scheduling algorithms.

**Advanced Features:**
- 3D aerodynamic blade design with compound sweep
- Blisk (bladed disk) construction in forward stages
- Active surge margin management
- Improved tip clearance control

**Common Fault Modes:**
- Compressor stall/surge (vibration exceedance)
- Variable vane actuator anomalies (sensor drift)
- Blade tip rub (EGT margin loss)
- FOD ingestion damage

#### 3.3.3 High-Pressure Turbine
**Part Number:** LEAP-HPT-1A32-300
**ATA Reference:** 72-51

The two-stage HPT features advanced single-crystal nickel superalloy blades with thermal barrier coating (TBC) and ceramic matrix composite (CMC) shrouds.

**CMC Shroud Benefits:**
- Operating temperature: 2,400°F (vs. 2,000°F for metal)
- Weight reduction: 66%
- Reduced cooling air: +1% efficiency gain

**Operating Limits:**
| Parameter | Normal | Caution | Maximum |
|-----------|--------|---------|---------|
| EGT (Takeoff, 5 min) | < 1,000°C | 1,000-1,040°C | 1,060°C |
| EGT (Max Continuous) | < 950°C | 950-980°C | 1,000°C |
| EGT (Start) | — | — | 750°C |
| Inter-turbine Temp | < 1,100°C | 1,100-1,150°C | 1,200°C |

#### 3.3.4 Main Fuel Pump
**Part Number:** LEAP-FP-1A32-400
**ATA Reference:** 73-21

The engine-driven fuel pump module integrates the fuel pump, fuel metering unit (FMU), and servo fuel heater into a single line-replaceable unit (LRU) for improved maintainability.

**Flow Rate:** 0.40 - 2.00 kg/s (normal operating range)

**Fuel System Features:**
- Variable geometry fuel nozzles
- Integrated debris monitoring
- FADEC-controlled fuel scheduling
- Automatic fuel recirculation for thermal management

#### 3.3.5 Thrust Bearing Assembly
**Part Number:** LEAP-TB-1A32-500
**ATA Reference:** 72-50

The #3 main bearing assembly is a duplex ball bearing with squeeze film damper, designed for the higher loads of the LEAP architecture.

**Advanced Features:**
- Ceramic hybrid rolling elements option
- Enhanced oil jet cooling
- Integrated speed sensor
- Prognostic wear detection

**Replacement Criteria:**
- Oil debris detection (chip detector or filter)
- Vibration signature change at bearing frequency
- Oil temperature rise > 15°C above baseline
- Time since overhaul exceeding 25,000 cycles

### 3.4 Normal Operating Parameters

| Parameter | Ground Idle | Flight Idle | Max Continuous | Takeoff |
|-----------|-------------|-------------|----------------|---------|
| N1Speed (% RPM) | 18-23% | 23-28% | 92% | 97% |
| N2 (% RPM) | 52-58% | 58-64% | 96% | 100% |
| EGT (°C) | 320-400 | 400-480 | 900-950 | 980-1040 |
| FuelFlow (kg/s) | 0.12-0.20 | 0.20-0.30 | 0.95-1.25 | 1.50-2.00 |
| Oil Pressure (psi) | 40-65 | 45-75 | 50-80 | 50-85 |
| Oil Temperature (°C) | 45-85 | 55-115 | 75-135 | 75-150 |
| Vibration N1 (ips) | < 0.8 | < 1.2 | < 2.0 | < 2.5 |
| Vibration N2 (ips) | < 0.6 | < 1.0 | < 1.8 | < 2.2 |

### 3.5 FADEC System

The LEAP-1A Full Authority Digital Engine Control provides:

- Automatic engine start with single-switch operation
- Thrust management with FLX/TOGA computation
- Fuel metering and scheduling
- Variable stator vane positioning
- Active clearance control management
- Bleed valve and variable bypass valve control
- Engine limit protection
- Comprehensive fault detection/isolation
- Data recording for trend monitoring

**FADEC Configuration:** Dual-channel with automatic switchover
**Software:** LEAP-1A Standard 2.3 (or as updated per SB)
**Manual Reversion:** Not available—FADEC failure requires engine shutdown

---

## 4. Engine Troubleshooting Procedures

### 4.1 Vibration Exceedance

**Fault Code:** ENG-VIB-001
**Severity Classification:** CRITICAL / MAJOR / MINOR
**Fleet Statistics:** Most common fault type (19% of engine events)

The LEAP-1A's lightweight composite fan and high bypass ratio make vibration monitoring particularly critical.

#### Vibration Limits (LEAP-1A Specific)

| Level | N1 Vibration | N2 Vibration | ECAM Alert |
|-------|--------------|--------------|------------|
| Normal | < 2.0 ips | < 1.8 ips | None |
| Caution | 2.0-3.0 ips | 1.8-2.5 ips | ENG 1(2) VIB (amber) |
| Warning | 3.0-4.0 ips | 2.5-3.5 ips | ENG 1(2) VIB HI (amber) |
| Limit | > 4.0 ips | > 3.5 ips | ENG 1(2) VIB (red) |

#### Common Root Causes (LEAP-1A)

| Cause | Frequency | Typical Indicator |
|-------|-----------|-------------------|
| Ice crystal icing | 30% | High altitude, humid conditions |
| Fan blade damage | 25% | 1×N1 frequency dominant |
| Bearing wear | 20% | Bearing-specific frequency |
| Core contamination | 15% | 1×N2 with EGT rise |
| Sensor/wiring fault | 10% | Erratic readings |

#### Ice Crystal Icing (LEAP-1A Specific Issue)

The LEAP-1A has experienced ice crystal icing events in high-altitude convective weather. This manifests as:
- Sudden vibration increase
- Possible rollback or flameout
- Recovery upon exiting icing conditions

**Operational Procedure:**
1. If vibration increases in suspected icing conditions, reduce thrust
2. Turn on engine anti-ice if not already on
3. Avoid areas of high ice water content (convective cells)
4. Document event for post-flight inspection

#### Troubleshooting Procedure

| Step | Action | Diagnostic Indicator |
|------|--------|---------------------|
| 1 | Download EMU data and vibration signature | Identify frequency and trend |
| 2 | Visual inspection of fan blades | Check for FOD, ice damage, delamination |
| 3 | Borescope HPC stages 1-3 | FOD, tip rub, blade damage |
| 4 | Review oil debris data | Bearing wear indication |
| 5 | Fan blade balance check | Imbalance > 0.1 oz-in requires correction |

#### Corrective Actions by Severity

**CRITICAL (Vibration > 4.0 ips N1 or > 3.5 ips N2):**
- Ground aircraft immediately
- Comprehensive borescope inspection all stages
- If blade damage found: Engine removal likely
- If ice event suspected: Document and monitor after inspection clears
- Estimated downtime: 24-72 hours minimum

**MAJOR (Vibration 2.5-4.0 ips):**
- Detailed fan blade inspection
- Borescope HPC and HPT
- Fan balance check and correction if needed
- May dispatch with enhanced monitoring per MEL

**MINOR (Vibration trending, within limits):**
- Document trend data
- Schedule detailed inspection within 500 FH
- Increase monitoring frequency

### 4.2 Contamination

**Fault Code:** ENG-CNT-002
**Severity Classification:** CRITICAL / MAJOR / MINOR
**Fleet Statistics:** Second most common fault (12% of engine events)

#### Contamination Types

| Type | Source | Effect | Detection |
|------|--------|--------|-----------|
| Volcanic ash | Environmental | Erosion, glass deposits | EGT rise, visual |
| Sand/dust | Ground ops, sandstorm | Compressor erosion | N2 trend, EGT margin |
| Oil contamination | Seal leak, overfill | Carbon deposits | Oil consumption, smoke |
| Ice crystal | High altitude | Combustor damage | Vibration, rollback |
| Sulfidation | Fuel sulfur, marine ops | HPT corrosion | EGT spread, borescope |

#### LEAP-1A Compressor Wash Procedure

The LEAP engine is approved for on-wing water wash to restore performance:

**Prerequisites:**
- EGT margin loss > 10°C from baseline
- No active faults or damage
- Ambient temperature > 5°C

**Procedure (Motoring Wash):**
1. Connect ground support equipment
2. Motor engine to 20% N2 using starter
3. Inject approved wash fluid (CFM WW-2)
4. Allow 10-minute soak period
5. Motor engine to purge wash fluid
6. Perform ground run to dry engine
7. Record EGT margin recovery

#### Corrective Actions

**CRITICAL (Severe contamination, inoperative):**
- Engine removal for shop cleaning
- HPT blade/vane replacement if sulfidation
- Complete oil system flush
- Estimated downtime: 5-7 days (engine swap)

**MAJOR (Performance degradation):**
- Perform compressor water wash
- Oil system service and sampling
- Monitor EGT margin recovery
- Schedule follow-up borescope in 250 FH

**MINOR (Early indicators):**
- Schedule water wash at next convenient opportunity
- Increase oil sampling frequency
- Document trend for fleet analysis

### 4.3 Overheat Conditions

**Fault Code:** ENG-OVH-003
**Severity Classification:** CRITICAL / MAJOR / MINOR
**Fleet Statistics:** 15% of engine maintenance events

#### EGT Exceedance Categories

| Category | Temperature | Duration | Required Action |
|----------|-------------|----------|-----------------|
| Start exceedance | > 750°C | Any | Abort start, inspect |
| Takeoff exceedance | > 1,060°C | > 5 sec | Borescope within 10 FH |
| Max continuous exceed | > 1,000°C | > 2 min | Borescope inspection |
| Hot start (hung) | EGT rising, N2 stagnant | — | Motor cool, inspect |

#### Troubleshooting Procedure

| Step | Action | Check For |
|------|--------|-----------|
| 1 | Review DFDR/QAR data | Peak EGT, duration, N1/N2 match |
| 2 | Compare EGT probe readings | Individual probe health (8 probes) |
| 3 | Borescope combustor and HPT | Thermal distress, coating loss |
| 4 | Check CMC shroud condition | Oxidation, spallation |
| 5 | Verify fuel nozzle spray patterns | Uneven fuel distribution |

#### CMC Shroud Inspection (LEAP-Specific)

The ceramic matrix composite HPT shrouds require specific inspection criteria:

| Condition | Acceptable | Requires Action |
|-----------|------------|-----------------|
| Surface oxidation | Light, uniform | Heavy, localized |
| Edge chipping | < 3mm | > 3mm or progressive |
| Coating loss | < 10% area | > 10% area |
| Cracking | None | Any visible crack |

### 4.4 Electrical Faults

**Fault Code:** ENG-ELF-004
**Severity Classification:** CRITICAL / MAJOR / MINOR
**Fleet Statistics:** 15% of engine maintenance events

#### Common Electrical Issues

| Component | Symptom | Typical Cause |
|-----------|---------|---------------|
| FADEC | Channel fault | Power supply, software |
| Speed sensors | N1/N2 disagree | Tone wheel, wiring |
| EGT probes | EGT spread | Probe failure, contamination |
| Oil sensors | Erratic readings | Contamination, wiring |
| EMU | Data dropouts | Communications fault |

#### FADEC Fault Isolation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Access FADEC fault log via CMC | List active and historical faults |
| 2 | Identify affected channel (A or B) | Determine which EEC has fault |
| 3 | Perform FADEC power cycle | Clear transient faults |
| 4 | Run FADEC BITE self-test | Verify internal diagnostics pass |
| 5 | Check EEC power supply | 115VAC and 28VDC within tolerance |

#### Corrective Actions

**CRITICAL (Dual channel fault, engine inoperative):**
- Engine shutdown required
- Replace affected EEC
- Full ground run verification
- Estimated downtime: 4-8 hours

**MAJOR (Single channel fault, degraded operation):**
- May dispatch per MEL with single-channel operation
- Schedule EEC replacement within 72 hours
- Document fault codes for CFM analysis

**MINOR (Intermittent, cleared faults):**
- Monitor for recurrence
- Check connector conditions
- Update software if applicable SB exists

### 4.5 Fuel Starvation

**Fault Code:** ENG-FUEL-005
**Severity Classification:** CRITICAL / MAJOR / MINOR
**Fleet Statistics:** 9% of engine maintenance events

#### Symptoms
- Fuel flow fluctuation or sudden drop
- N1/N2 rollback
- EGT rise (lean mixture)
- Possible flameout

#### Diagnostic Procedure

| Step | Action | Check Point |
|------|--------|-------------|
| 1 | Verify fuel quantity and feed configuration | Rule out fuel management error |
| 2 | Check fuel filter differential pressure | > 12 psi indicates blockage |
| 3 | Review fuel pump delivery pressure | Nominal: 1,000-1,400 psi |
| 4 | Inspect fuel metering unit operation | FADEC command vs actual position |
| 5 | Check for fuel system leaks | Visual and pressure decay test |
| 6 | Sample fuel for contamination | Water, particulates, microbial |

---

## 5. Avionics System

### 5.1 System Overview

The A321neo features the Airbus A320neo avionics suite with enhanced capabilities including improved FMS, FANS-C datalink, and ADS-B Out compliance.

### 5.2 Component Descriptions

#### 5.2.1 Flight Management System (FMS)
**Part Number:** AVN-FMS-A321N-100
**ATA Reference:** 34-61

The dual FMS provides:
- 4D trajectory management
- RNP AR 0.1 approach capability
- FANS-C/CPDLC datalink
- Performance optimization with LEAP engine models
- Flex thrust calculations

**Database Updates:** Navigation database update every 28 days (AIRAC cycle)

#### 5.2.2 Air Data Computer (ADC)
**Part Number:** AVN-ADIRU-A321N-200
**ATA Reference:** 34-11

Three Air Data Inertial Reference Units (ADIRU) provide:
- Barometric altitude (4 static ports)
- Calibrated airspeed (3 pitot probes)
- Angle of attack (3 AOA vanes)
- Inertial position and attitude

**AOA Sensor Monitoring:** Post-737 MAX, enhanced AOA disagree alerting is installed.

#### 5.2.3 Navigation Receiver (NAV)
**Part Number:** AVN-MMR-A321N-300
**ATA Reference:** 34-51

Multi-Mode Receiver providing:
- GPS L1/L5 dual frequency
- SBAS (WAAS/EGNOS)
- GBAS Cat III capability
- VOR/DME and ILS
- Integrated TCAS/ADS-B

### 5.3 Avionics Troubleshooting

#### 5.3.1 Sensor Drift

**Fault Code:** AVN-SDR-001
**Fleet Statistics:** 11% of avionics events

**Diagnostic Steps:**
1. Compare ADIRU 1/2/3 outputs on maintenance page
2. Cross-check with GPS-derived altitude
3. Review AOA sensor agreement
4. Check pitot/static system for leaks or blockage
5. Verify ADIRU alignment quality

#### 5.3.2 Electrical Faults (Avionics)

**Fault Code:** AVN-ELF-002
**Fleet Statistics:** 15% of avionics events

**Common Causes:**
- Power supply interruption
- Cooling system degradation
- Connector corrosion (especially in humid environments)
- Software anomalies

---

## 6. Hydraulics System

### 6.1 System Overview

The A321neo hydraulic system is a three-system architecture (Green, Blue, Yellow) operating at 3,000 psi, enhanced from the A320ceo with improved pump efficiency.

### 6.2 System Architecture

| System | Color | Power Source | Primary Functions |
|--------|-------|--------------|-------------------|
| Green | Green | EDP (Engine 1) | Flight controls, slats, gear, NWS |
| Blue | Blue | Electric pump, RAT | Flight controls, slats/flaps |
| Yellow | Yellow | EDP (Engine 2), Electric pump | Flight controls, flaps, cargo doors |

### 6.3 Component Descriptions

#### 6.3.1 Main Hydraulic Pump (Engine-Driven)
**Part Number:** HYD-EDP-A321N-100
**ATA Reference:** 29-11

Variable-displacement piston pump:
- Operating pressure: 3,000 psi nominal
- Flow rate: 34 gpm at 3,000 psi
- Case drain limit: 3 gpm
- Integrated filter and pressure relief

#### 6.3.2 Hydraulic Reservoir
**Part Number:** HYD-RES-A321N-200
**ATA Reference:** 29-21

Bootstrap-type pressurized reservoir:
- Green reservoir: 18.5 liters
- Blue reservoir: 6.5 liters
- Yellow reservoir: 14.5 liters
- Operating temperature: -54°C to +135°C
- Fluid type: Skydrol LD-4 or HyJet V

#### 6.3.3 Flap Actuator (Power Control Unit)
**Part Number:** HYD-FLAP-A321N-300
**ATA Reference:** 29-31

The A321neo flap system uses:
- Dual-motor Power Control Unit
- Asymmetry protection via SFCC
- Position feedback to flight control computers

### 6.4 Hydraulics Troubleshooting

#### 6.4.1 Leak Detection

**Fault Code:** HYD-LEAK-001
**Fleet Statistics:** 50% of hydraulics events

**Common Leak Locations:**

| System | Location | Access |
|--------|----------|--------|
| Green | EDP nose seal | Engine cowl |
| Green | Landing gear actuators | Wheel wells |
| Blue | Electric pump shaft | E/E bay |
| Yellow | Cargo door actuators | Cargo compartment |
| All | Flexible hoses at wings | Wing panels |

#### 6.4.2 Contamination

**Fault Code:** HYD-CNT-002
**Fleet Statistics:** 22% of hydraulics events

**Contamination Analysis (NAS 1638):**

| Class | Particles/100ml | Action |
|-------|-----------------|--------|
| 6 or better | < 2,500 (5-15μ) | Acceptable |
| 7 | 2,500-5,000 | Resample in 300 FH |
| 8 | 5,000-10,000 | Filter, resample |
| 9+ | > 10,000 | Flush system |

---

## 7. Fault Code Reference

### 7.1 Engine Fault Codes

| Code | Description | Severity | ATA | Primary Action |
|------|-------------|----------|-----|----------------|
| ENG-VIB-001 | Vibration Exceedance | CRIT/MAJ/MIN | 72 | Fan inspection, balance |
| ENG-CNT-002 | Contamination | CRIT/MAJ/MIN | 72 | Water wash, borescope |
| ENG-OVH-003 | Overheat (EGT) | CRIT/MAJ/MIN | 72 | Borescope, CMC inspect |
| ENG-ELF-004 | Electrical Fault | CRIT/MAJ/MIN | 77 | FADEC diagnostics |
| ENG-FUEL-005 | Fuel Starvation | CRIT/MAJ | 73 | Fuel system check |
| ENG-SDR-006 | Sensor Drift | MAJ/MIN | 77 | EMU diagnostics |
| ENG-BRG-007 | Bearing Wear | CRIT/MAJ/MIN | 72 | Oil analysis |
| ENG-LEAK-008 | Fluid Leak | MAJ/MIN | 79 | Identify and repair |

### 7.2 Avionics Fault Codes

| Code | Description | Severity | ATA | Primary Action |
|------|-------------|----------|-----|----------------|
| AVN-SDR-001 | Sensor Drift | MAJ/MIN | 34 | ADIRU comparison |
| AVN-ELF-002 | Electrical Fault | CRIT/MAJ/MIN | 34 | Power, cooling check |
| AVN-FMS-003 | FMS Malfunction | MAJ | 34 | Reset, database reload |
| AVN-NAV-004 | NAV/GPS Fault | MIN | 34 | Antenna, MMR check |
| AVN-AOA-005 | AOA Disagree | MAJ | 34 | AOA sensor inspection |

### 7.3 Hydraulics Fault Codes

| Code | Description | Severity | ATA | Primary Action |
|------|-------------|----------|-----|----------------|
| HYD-LEAK-001 | System Leak | CRIT/MAJ/MIN | 29 | Locate, repair |
| HYD-CNT-002 | Contamination | MAJ/MIN | 29 | Sample, filter/flush |
| HYD-PRS-003 | Low Pressure | CRIT/MAJ | 29 | Pump, leak check |
| HYD-QTY-004 | Low Quantity | MAJ | 29 | Replenish, leak check |
| HYD-OVHT-005 | Overheat | MAJ | 29 | Reduce demand, inspect |

### 7.4 Severity Definitions

| Level | Definition | Response Time | Dispatch |
|-------|------------|---------------|----------|
| CRITICAL | Flight safety affected | Before next flight | No-go |
| MAJOR | System degraded | 1-10 days | Per MEL |
| MINOR | Limited impact | Next scheduled mx | Normal |

---

## 8. Troubleshooting Decision Trees

### 8.1 Engine Vibration Diagnostic Flow (LEAP-1A)

```
START: Engine Vibration Warning/Caution
│
├─► Is this occurring in suspected icing conditions?
│   │
│   ├─► YES ─► Reduce thrust, ensure anti-ice ON
│   │          Monitor for vibration decrease
│   │          If persists > 30 sec at reduced thrust:
│   │          └─► Consider engine shutdown
│   │          └─► Post-flight: Ice crystal inspection
│   │
│   └─► NO ─► Continue to vibration analysis
│
├─► Is vibration > 4.0 ips (N1) or > 3.5 ips (N2)?
│   │
│   ├─► YES ─► Reduce thrust to idle
│   │          If vibration remains high: Shutdown engine
│   │          └─► END: Engine removal likely
│   │
│   └─► NO ─► Continue troubleshooting
│
├─► Analyze frequency spectrum (EMU data download)
│   │
│   ├─► 1×N1 dominant
│   │   ├─► Inspect composite fan blades for damage
│   │   ├─► Check for delamination, matrix cracks
│   │   ├─► Perform fan balance if imbalance found
│   │   └─► END: Fan service
│   │
│   ├─► 1×N2 dominant
│   │   ├─► Borescope HPC stages 1-5
│   │   ├─► Check oil analysis for core bearing wear
│   │   └─► END: Core inspection
│   │
│   └─► Bearing frequency
│       ├─► Immediate oil sample (SOAP/ferrography)
│       ├─► If elevated metals: Plan engine removal
│       └─► END: Bearing replacement (shop)
│
└─► Vibration cleared/transient?
    ├─► Document fully for trend analysis
    └─► END: Monitor with enhanced frequency
```

### 8.2 EGT Exceedance Investigation

```
START: EGT Limit Exceedance Recorded
│
├─► Was exceedance during start?
│   │
│   ├─► YES (> 750°C)
│   │   ├─► Hot start likely
│   │   ├─► Allow engine to cool (30+ minutes)
│   │   ├─► Borescope combustor and HPT
│   │   ├─► If damage: Engine removal
│   │   └─► If clear: Attempt restart with enhanced monitoring
│   │
│   └─► NO ─► Continue
│
├─► Was exceedance during takeoff/climb?
│   │
│   ├─► > 1,060°C for > 5 seconds
│   │   ├─► Ground aircraft
│   │   ├─► Full HPT borescope inspection
│   │   ├─► Inspect CMC shrouds for thermal damage
│   │   └─► END: Engineering assessment required
│   │
│   └─► < 1,060°C, brief
│       ├─► Document in log
│       ├─► Schedule borescope within 100 FH
│       └─► END: Monitor EGT margin trend
│
├─► Check individual EGT probe readings
│   │
│   ├─► Single probe outlier
│   │   ├─► Suspect probe failure
│   │   ├─► Replace suspect probe
│   │   └─► END: Sensor replacement
│   │
│   └─► All probes elevated uniformly
│       ├─► Actual engine condition
│       ├─► Check fuel nozzles for blockage
│       ├─► Borescope for deposits/damage
│       └─► END: Engine service required
│
└─► EGT margin trending down over time?
    ├─► > 20°C loss: Schedule compressor wash
    └─► END: Trend monitoring
```

### 8.3 Composite Fan Blade Damage Assessment

```
START: Fan Blade Damage Reported/Suspected
│
├─► Perform detailed visual inspection
│   │
│   ├─► Leading edge damage (titanium sheath)
│   │   ├─► Nick < 3mm depth: Monitor, MEL permitting
│   │   ├─► Nick 3-6mm: Requires engineering disposition
│   │   └─► Nick > 6mm or gouge: Blade replacement
│   │
│   ├─► Composite body damage
│   │   ├─► Surface scratch only: Document, monitor
│   │   ├─► Matrix cracking visible: Engineering review
│   │   └─► Delamination suspected: Blade replacement
│   │
│   └─► Trailing edge damage
│       ├─► Chip < 10mm: May be acceptable
│       └─► Chip > 10mm: Engineering review
│
├─► Is damage from FOD event?
│   │
│   ├─► YES
│   │   ├─► Inspect all 18 blades
│   │   ├─► Borescope core for debris passage
│   │   ├─► If debris passed to HPT: Engine removal
│   │   └─► If contained to fan: Assess per above
│   │
│   └─► NO (fatigue, erosion)
│       └─► Single blade: Replace and trend fleet
│
└─► CFM engineering disposition required?
    ├─► Submit photos and measurements
    ├─► Await disposition (typically 24-48 hours)
    └─► END: Per CFM guidance
```

---

## 9. Scheduled Maintenance Tasks

### 9.1 Engine Inspection Schedule

| Task | Interval | Duration | Personnel |
|------|----------|----------|-----------|
| Fan blade visual (composite) | 750 FH | 1.0 hr | 1 mechanic |
| Engine oil service | 100 FH or 14 days | 0.5 hr | 1 mechanic |
| Oil filter inspection | 600 FH | 1.0 hr | 1 mechanic |
| Chip detector check | 600 FH | 0.5 hr | 1 mechanic |
| Borescope - HPC | 4,000 FH | 3.5 hr | 1 specialist |
| Borescope - Combustor | 4,000 FH | 2.5 hr | 1 specialist |
| Borescope - HPT/CMC shrouds | 4,000 FH | 3.0 hr | 1 specialist |
| Compressor water wash | As needed | 4.0 hr | 2 mechanics |
| Fuel filter replacement | 1,500 FH | 1.5 hr | 1 mechanic |
| EMU data download | Weekly | 0.5 hr | 1 technician |

### 9.2 Avionics Inspection Schedule

| Task | Interval | Duration | Personnel |
|------|----------|----------|-----------|
| FMS database update | 28 days | 0.5 hr | 1 technician |
| ADIRU accuracy check | 12 months | 3.0 hr | 1 technician |
| Pitot-static leak test | 24 months | 4.0 hr | 1 technician |
| AOA sensor calibration | 24 months | 2.0 hr | 1 technician |
| GPS/MMR accuracy check | 12 months | 2.0 hr | 1 technician |
| BITE fault log review | Weekly | 0.5 hr | 1 technician |

### 9.3 Hydraulics Inspection Schedule

| Task | Interval | Duration | Personnel |
|------|----------|----------|-----------|
| Fluid level check | Daily | 0.25 hr | 1 mechanic |
| Fluid sampling | 600 FH | 0.5 hr | 1 mechanic |
| System filter change | 1,500 FH | 2.5 hr | 1 mechanic |
| EDP inspection | A-check | 2.5 hr | 1 mechanic |
| Reservoir inspection | C-check | 3.0 hr | 2 mechanics |

### 9.4 Common Task Cards

#### Task Card: ENG-TC-001 - Composite Fan Blade Inspection

**Purpose:** Detailed inspection of LEAP-1A carbon fiber fan blades

**Reference:** AMM 72-21-00

**Tools Required:**
- Inspection mirror (articulating)
- LED flashlight (white light)
- Borescope (optional for blade root)
- Magnifying glass (10x)
- Blade measurement template (P/N: LEAP-TOOL-FB1)

**Procedure:**
1. Position aircraft in suitable lighting (hangar preferred)
2. Open fan cowl doors fully
3. Manually rotate fan to inspect each blade (18 total)
4. For each blade, inspect:
   - Leading edge (titanium sheath): nicks, erosion, debonding
   - Composite body: cracks, delamination, impact marks
   - Trailing edge: chips, erosion
   - Blade root: fretting, corrosion
5. Document any findings with photos
6. Compare to AMM limits and CFM service letters
7. Record inspection in aircraft log

**Acceptance Criteria:** Per CFM LEAP-1A AMM 72-21-00

#### Task Card: HYD-TC-001 - Hydraulic Fluid Sample

**Purpose:** Obtain fluid sample for contamination analysis

**Procedure:**
1. Ensure system depressurized
2. Locate sample port on reservoir
3. Clean area around port
4. Flush 50ml before taking sample
5. Collect 100ml in clean bottle
6. Label: A/C reg, system (G/B/Y), date, FH
7. Submit to lab within 48 hours

---

## 10. Appendices

### 10.1 Quick Reference - Normal Operating Limits

#### Engine Parameters (LEAP-1A)

| Parameter | Ground Idle | Flight Idle | Max Continuous | Takeoff (5 min) |
|-----------|-------------|-------------|----------------|-----------------|
| N1Speed (%) | 18-23 | 23-28 | 92 | 97 |
| N2 (%) | 52-58 | 58-64 | 96 | 100 |
| EGT (°C) | 320-400 | 400-480 | 950 | 1,040 |
| Oil Pressure (psi) | 40-65 | 45-75 | 50-80 | 50-85 |
| Oil Temp (°C) | 45-85 | 55-115 | 75-135 | 75-150 |
| Vibration N1 (ips) | < 0.8 | < 1.2 | < 2.0 | < 2.5 |
| Vibration N2 (ips) | < 0.6 | < 1.0 | < 1.8 | < 2.2 |

#### Hydraulic System

| Parameter | Green | Blue | Yellow |
|-----------|-------|------|--------|
| Pressure | 2,900-3,100 psi | 2,900-3,100 psi | 2,900-3,100 psi |
| Quantity | 70-100% | 70-100% | 70-100% |
| Fluid Temp | -40 to +107°C | -40 to +107°C | -40 to +107°C |

### 10.2 Abbreviations and Acronyms

| Abbreviation | Definition |
|--------------|------------|
| ADIRU | Air Data Inertial Reference Unit |
| AFDX | Avionics Full-Duplex Switched Ethernet |
| AOA | Angle of Attack |
| CMC | Ceramic Matrix Composite |
| CPDLC | Controller-Pilot Datalink Communications |
| EMU | Engine Monitoring Unit |
| EGT | Exhaust Gas Temperature |
| FADEC | Full Authority Digital Engine Control |
| FANS | Future Air Navigation System |
| FMS | Flight Management System |
| GBAS | Ground-Based Augmentation System |
| HPC | High Pressure Compressor |
| HPT | High Pressure Turbine |
| LEAP | Leading Edge Aviation Propulsion |
| MEL | Minimum Equipment List |
| MMR | Multi-Mode Receiver |
| RNP | Required Navigation Performance |
| RTM | Resin Transfer Molding |
| SBAS | Space-Based Augmentation System |
| SFCC | Slat/Flap Control Computer |
| TAPS | Twin Annular Premixing Swirler |

### 10.3 Reference Documents

| Document | Number | Description |
|----------|--------|-------------|
| Aircraft Maintenance Manual | AMM A321neo | Primary maintenance reference |
| Fault Isolation Manual | FIM A321neo | Troubleshooting guidance |
| Component Maintenance Manual | CMM LEAP-1A | Engine overhaul data |
| Service Bulletin Index | SB A321neo | Modification tracking |
| CFM Service Letters | SL LEAP-1A | Engine-specific guidance |
| Airworthiness Directives | AD List | Mandatory compliance |

### 10.4 Emergency Contacts

| Function | Contact | Availability |
|----------|---------|--------------|
| AOG Desk | +1-800-555-0321 | 24/7 |
| Engine Support (CFM) | +1-513-555-0532 | 24/7 |
| Airbus Technical Support | +33-5-555-0100 | 24/7 |
| Technical Records | tech.records@regionalco.com | 24/7 |
| Engineering Support | engineering@regionalco.com | 24/7 |
| Parts Supply | parts@regionalco.com | 24/7 |

### 10.5 Fleet Maintenance Statistics Summary

Based on fleet data analysis (July - September 2024):

| Metric | Value |
|--------|-------|
| Total Maintenance Events | 74 |
| Critical Events | 25 (34%) |
| Major Events | 17 (23%) |
| Minor Events | 32 (43%) |
| Engine-Related | 45 (61%) |
| Avionics-Related | 15 (20%) |
| Hydraulics-Related | 14 (19%) |

**Top Fault Types:**
1. Vibration Exceedance - 14 events (19%)
2. Electrical Fault - 11 events (15%)
3. Overheat - 11 events (15%)
4. Contamination - 9 events (12%)
5. Leak - 9 events (12%)
6. Fuel Starvation - 7 events (9%)
7. Sensor Drift - 8 events (11%)
8. Bearing Wear - 5 events (7%)

**Corrective Action Distribution:**
1. Adjusted tolerance - 18 (24%)
2. Cleaned and reassembled - 17 (23%)
3. Inspected and found no fault - 16 (22%)
4. Replaced component - 12 (16%)
5. Software patch applied - 11 (15%)

### 10.6 Revision History Log

| Page | Rev | Date | Change Description |
|------|-----|------|--------------------|
| All | 1.0 | 2024-10-01 | Initial release |

---

**END OF DOCUMENT**

*This manual is for demonstration purposes. Always refer to official Airbus documentation for actual maintenance procedures.*
