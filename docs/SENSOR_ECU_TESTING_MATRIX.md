# Sensor & ECU Testing Matrix - Living Document

**BCScanTool v2.0 - Comprehensive Fault Induction Protocol**

**Created:** January 13, 2026 **Last Updated:** January 13, 2026 **Version:** 1.0

---

## 🎯 Purpose

This living document catalogs every possible sensor manipulation, ECU test, and fault condition we can safely induce to train and validate our ML models. Add new tests as you discover them!

---

## 📊 Test Categories

### Risk Levels:

- 🟢 **LOW:** Safe, quick disconnect/reconnect, no damage risk
- 🟡 **MODERATE:** Requires care, brief test only, minor stress on components
- 🔴 **HIGH:** Potential for damage if done incorrectly or too long, expert only

### Test Types:

- **\[E\]** Electrical (unplugs, shorts, voltage manipulation)
- **\[M\]** Mechanical (restrictions, blockages, physical interference)
- **\[S\]** Simulated (fake signals, CAN injection)
- **\[ECU\]** ECU manipulation (software, parameters, reflash)

---

## 1. AIR INTAKE SYSTEM TESTS 💨

### 1.1 MAF Sensor Tests \[E\]

#### Test 1.1.1: Full MAF Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0101, P0102, P0171, P0174

Procedure:
1. Baseline scan (normal operation)
2. Unplug MAF electrical connector
3. Start engine, let stabilize
4. Capture fault scan
5. Reconnect, clear codes, verify

Expected Behavior:
- Engine runs rough, high idle
- ECU uses default airflow values
- Fuel trims go highly positive (lean compensation)
- Reduced power, sluggish throttle response

ML Training Value: HIGH - Clear electrical fault signature
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 1.1.2: MAF Signal Wire Short 🟡

```
Risk: MODERATE
Duration: 1-2 minutes
Expected Codes: P0102 (low input)

Procedure:
1. Baseline scan
2. Short MAF signal wire to ground (using jumper wire)
   - Locate signal wire (usually pin 5)
   - Briefly touch to ground
3. Capture scan showing 0V signal
4. Remove short immediately
5. Verify restoration

Expected Behavior:
- MAF reads 0 g/s or very low
- Similar to full disconnect but different fault code
- Engine may not start or run very poorly

ML Training Value: HIGH - Different fault signature than disconnect
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 1.1.3: MAF Contamination Simulation \[M\] 🟢

```
Risk: LOW
Duration: 3-5 minutes
Expected Codes: P0101 (range/performance)

Procedure:
1. Baseline scan
2. Spray light mist of water into air intake (before MAF)
   - Creates temporary contamination
   - Simulates dirty/failing MAF
3. Capture scan showing erratic readings
4. Let dry, verify restoration

Expected Behavior:
- Erratic MAF readings
- Fluctuating idle
- Poor throttle response
- Possible P0101 (range issue, not complete failure)

ML Training Value: MODERATE - Intermittent fault pattern
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 1.1.4: Restricted Airflow \[M\] 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: None or P0171/P0174 (lean)

Procedure:
1. Baseline scan
2. Partially block air intake with rag/tape
   - Cover 50-75% of air filter opening
3. Rev engine gently, capture scan
4. Remove restriction
5. Verify restoration

Expected Behavior:
- Low MAF readings despite throttle input
- Engine struggles under load
- Possible lean codes (can't get enough air)
- High fuel trims

ML Training Value: MODERATE - Mechanical restriction vs sensor failure
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 2. OXYGEN SENSOR TESTS 🔥

### 2.1 Bank 1 Sensor 1 (Front O2) \[E\]

#### Test 2.1.1: Full O2 Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0131, P0132, P0133

Procedure:
1. Baseline scan
2. Unplug B1S1 O2 sensor connector
3. Engine running, capture scan
4. Reconnect, clear codes

Expected Behavior:
- Fixed O2 voltage (0V or reference voltage)
- ECU switches to open-loop mode
- Fuel trims lose closed-loop correction
- Engine may run slightly rich

ML Training Value: HIGH - Clear sensor failure
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 2.1.2: O2 Sensor Heater Failure Simulation 🟡

```
Risk: MODERATE
Duration: 3-5 minutes (cold start only)
Expected Codes: P0135 (heater circuit)

Procedure:
1. Cold engine, disconnect O2 heater wires only
   - Leave signal wires connected
2. Start engine, capture scan
3. Monitor O2 taking much longer to heat up
4. Reconnect heater, verify

Expected Behavior:
- Slow O2 sensor response
- Extended open-loop operation
- Slow warmup, delayed closed-loop
- P0135 heater circuit code

ML Training Value: MODERATE - Degraded sensor vs total failure
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 2.1.3: Bank 2 Sensor 1 (Other Front O2) \[E\] 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0151, P0152, P0153

Same procedure as 2.1.1 but for opposite bank
Valuable for comparing bank-specific faults

ML Training Value: HIGH - Multi-bank fault detection
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 2.1.4: Downstream O2 Sensors (After Cat) \[E\] 🟢

```
Risk: LOW
Duration: 3-5 minutes
Expected Codes: P0141, P0161 (heater), P0138, P0158 (signal)

Procedure:
1. Baseline scan
2. Disconnect rear O2 sensor(s)
3. Drive/run engine
4. Capture scan - mainly affects catalyst monitor

Expected Behavior:
- Less impact on fuel trims (rears are for cat monitoring)
- Catalyst efficiency codes possible
- Engine runs normally but emissions monitoring disabled

ML Training Value: MODERATE - Different role than front O2s
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 3. THROTTLE & ACCELERATOR TESTS 🚗

### 3.1 Throttle Position Sensor \[E\]

#### Test 3.1.1: TPS Disconnect 🟡

```
Risk: MODERATE
Duration: 1-2 minutes MAX
Expected Codes: P0120, P0121, P0122

⚠️ WARNING: May cause throttle to stay wide open on some vehicles (failsafe mode)

Procedure:
1. Baseline scan (engine OFF for safety)
2. Disconnect TPS connector
3. Key on, engine off - capture scan
4. Attempt to start engine (may not start or run very poorly)
5. Immediately reconnect if issues
6. Clear codes

Expected Behavior:
- Fixed throttle position reading
- Limp mode activated
- Engine may not start or runs at fixed RPM
- No throttle response

ML Training Value: HIGH - Critical sensor failure
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 3.1.2: Accelerator Position Sensor Disconnect 🟡

```
Risk: MODERATE
Duration: 1-2 minutes
Expected Codes: P0222, P0223

Procedure:
1. Baseline scan
2. Disconnect accelerator pedal position sensor
3. Key on, engine off first
4. Attempt start (may not allow)
5. Capture scan
6. Reconnect

Expected Behavior:
- Throttle body receives no pedal input
- May prevent starting (safety feature)
- Limp mode if it starts
- Fixed idle only

ML Training Value: HIGH - Drive-by-wire failure mode
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 4. FUEL SYSTEM TESTS ⛽

### 4.1 Fuel Injector Tests \[E\]

#### Test 4.1.1: Single Injector Disconnect 🔴

```
Risk: HIGH - Can cause misfire, catalyst damage if too long
Duration: 30-60 seconds MAX
Expected Codes: P0300, P030X (cylinder X misfire)

Procedure:
1. Baseline scan
2. Disconnect ONE fuel injector (Cylinder 1)
3. Start engine briefly
4. Capture scan showing misfire
5. IMMEDIATELY reconnect
6. Clear codes, verify

Expected Behavior:
- Obvious cylinder misfire
- Rough running
- Flashing CEL
- Unburned fuel to exhaust (catalyst damage risk)

ML Training Value: VERY HIGH - Misfire detection critical
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 4.1.2: Fuel Pressure Regulator Vacuum Line Disconnect \[M\] 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: Possibly P0172 (rich)

Procedure:
1. Baseline scan
2. Disconnect vacuum line to fuel pressure regulator
3. Engine running, capture scan
4. Reconnect vacuum line

Expected Behavior:
- Higher fuel pressure (no vacuum reference)
- Slightly rich condition
- Possible black smoke
- Negative fuel trims (ECU compensating)

ML Training Value: MODERATE - Fuel system pressure issue
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 5. IGNITION SYSTEM TESTS ⚡

### 5.1 Ignition Coil Tests \[E\]

#### Test 5.1.1: Single Coil Disconnect 🔴

```
Risk: HIGH - Misfire, catalyst damage risk
Duration: 30-60 seconds MAX
Expected Codes: P0300, P030X

Procedure:
1. Baseline scan
2. Disconnect ONE ignition coil
3. Start engine BRIEFLY
4. Capture misfire scan
5. IMMEDIATELY reconnect
6. Clear codes

Expected Behavior:
- Cylinder misfire (no spark)
- Very rough running
- Flashing CEL
- Similar to injector disconnect but different signature

ML Training Value: VERY HIGH - Compare vs injector misfire
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 5.1.2: Spark Plug Wire Resistance \[M\] 🟡

```
Risk: MODERATE
Duration: 2-3 minutes
Expected Codes: P030X (intermittent misfire)

Procedure:
1. Baseline scan
2. Add resistor in series with spark plug wire (if accessible)
   - Simulates degraded wire
3. Capture scan with intermittent misfire
4. Remove resistor

Expected Behavior:
- Weak spark
- Occasional misfires under load
- Less obvious than full disconnect

ML Training Value: HIGH - Degraded vs failed component
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 6. COOLING SYSTEM TESTS 🌡️

### 6.1 Temperature Sensor Tests \[E\]

#### Test 6.1.1: Coolant Temp Sensor Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0117, P0118

Procedure:
1. Baseline scan (engine cold is better)
2. Disconnect coolant temp sensor
3. Key on, capture scan
4. Start engine (if safe - will show default temp)
5. Reconnect

Expected Behavior:
- ECT shows -40°F or 300°F (out of range)
- ECU uses default coolant temp
- Engine may run rough (wrong fuel strategy)
- Cooling fans may run constantly

ML Training Value: HIGH - Critical sensor for fuel/ignition timing
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 6.1.2: Coolant Temp Sensor Resistance Change \[M\] 🟡

```
Risk: MODERATE
Duration: 3-5 minutes
Expected Codes: P0125 (insufficient temp)

Procedure:
1. Baseline scan (warm engine)
2. Add resistor in series with ECT signal
   - Simulates cooler temp than actual
3. Capture scan showing false low temp
4. Remove resistor

Expected Behavior:
- ECU thinks engine is colder than it is
- Runs richer than needed
- Possible rough running when warm
- May not enter closed-loop

ML Training Value: HIGH - Sensor drift vs total failure
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 6.1.3: Intake Air Temp Sensor Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0112, P0113

Procedure:
1. Baseline scan
2. Disconnect IAT sensor
3. Capture scan
4. Reconnect

Expected Behavior:
- IAT shows extreme value (-40°F or 300°F)
- ECU uses default value
- Minor impact on fuel/timing strategy

ML Training Value: MODERATE - Less critical than ECT
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 7. VACUUM & PRESSURE TESTS 💨

### 7.1 Vacuum Leak Tests \[M\]

#### Test 7.1.1: PCV Valve Hose Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0171, P0174 (lean)

Procedure:
1. Baseline scan
2. Disconnect PCV valve hose (creates vacuum leak)
3. Engine running, capture scan
4. Reconnect hose

Expected Behavior:
- Unmetered air entering intake
- High idle (1200-1500 RPM)
- Positive fuel trims (ECU adding fuel)
- Possible rough running
- Lean codes

ML Training Value: VERY HIGH - Common real-world issue
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 7.1.2: Brake Booster Vacuum Line Disconnect 🟡

```
Risk: MODERATE - Affects brake assist!
Duration: 1-2 minutes, vehicle stationary
Expected Codes: P0171, P0174

⚠️ WARNING: Reduces brake assist effectiveness

Procedure:
1. Baseline scan
2. Disconnect brake booster vacuum line
3. Engine running, parked only
4. Capture scan
5. Immediately reconnect
6. Test brakes before driving

Expected Behavior:
- Larger vacuum leak than PCV
- Higher idle, more pronounced effect
- High positive fuel trims
- Lean codes

ML Training Value: HIGH - Varying vacuum leak sizes
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 7.1.3: Intake Manifold Gasket Leak Simulation \[M\] 🔴

```
Risk: HIGH - Do not over-rev engine
Duration: 1-2 minutes MAX
Expected Codes: P0171, P0174, possible P0300 (misfire)

Procedure:
1. Baseline scan
2. Loosen one intake manifold bolt slightly
   - Creates small controlled leak
   - DO NOT REMOVE bolt
3. Very brief idle test
4. Capture scan
5. Immediately retighten to spec

Expected Behavior:
- Vacuum leak affecting one or more cylinders
- Rough idle, possible misfire
- Lean condition
- Uneven fuel trims between banks

ML Training Value: HIGH - Localized vs system-wide leak
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 8. EXHAUST & EMISSIONS TESTS 🏭

### 8.1 EGR System Tests \[M\]

#### Test 8.1.1: EGR Valve Disconnect 🟢

```
Risk: LOW
Duration: 3-5 minutes
Expected Codes: P0401 (insufficient flow)

Procedure:
1. Baseline scan
2. Disconnect EGR valve vacuum line or electrical connector
3. Drive vehicle (need load for EGR to activate)
4. Capture scan showing EGR fault
5. Reconnect

Expected Behavior:
- No EGR flow when commanded
- P0401 insufficient flow
- May run slightly hotter
- Possible rough idle if EGR was stuck open

ML Training Value: MODERATE - Emissions system fault
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 8.1.2: EGR Valve Manually Opened \[M\] 🟡

```
Risk: MODERATE
Duration: 1-2 minutes
Expected Codes: P0400, P0402 (excessive flow)

Procedure:
1. Baseline scan (idle)
2. Manually hold EGR valve open (if accessible)
3. Capture scan at idle with excess EGR
4. Release EGR valve

Expected Behavior:
- Excess exhaust gas at idle
- Very rough running
- Possible stalling
- P0402 excessive EGR flow

ML Training Value: HIGH - Stuck-open vs stuck-closed EGR
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 9. CAMSHAFT & TIMING TESTS ⚙️

### 9.1 Variable Valve Timing (VVT) Tests \[E\]

#### Test 9.1.1: VVT Solenoid Disconnect 🟢

```
Risk: LOW
Duration: 3-5 minutes
Expected Codes: P0010, P0011, P0020, P0021 (VVT system)

Procedure:
1. Baseline scan
2. Disconnect VVT oil control solenoid
3. Rev engine gently, capture scan
4. Reconnect

Expected Behavior:
- Fixed cam timing (no VVT adjustment)
- Loss of power at certain RPM ranges
- Possible rough running
- VVT system codes

ML Training Value: MODERATE - Variable timing fault
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 10. ELECTRICAL SYSTEM TESTS 🔋

### 10.1 Charging System Tests \[E\]

#### Test 10.1.1: Alternator Disconnect (Engine Running) 🔴

```
Risk: HIGH - Can damage electrical system
Duration: 30 seconds MAX
Expected Codes: P0560 (system voltage)

⚠️ WARNING: Can cause voltage spikes, damage electronics

Procedure:
1. Baseline scan
2. Engine running, disconnect alternator (output wire, NOT ground)
3. VERY BRIEF test (30 sec max)
4. Capture scan showing voltage drop
5. Immediately reconnect

Expected Behavior:
- Battery voltage drops (no charging)
- System voltage low (11-12V)
- Voltage warning light
- Systems may shut down

ML Training Value: HIGH - Charging system failure
Note: ALTERNATOR WAS ACTUAL ISSUE - Good test validation!
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 10.1.2: Battery Terminal Corrosion Simulation \[E\] 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: Possible P0562 (low voltage)

Procedure:
1. Baseline scan (engine off)
2. Add high-resistance connection to battery terminal
   - Wrap terminal with layer of paper before reconnecting
3. Attempt start, capture scan
4. Remove paper, clean connection

Expected Behavior:
- High resistance = voltage drop
- Slow cranking
- Possible no-start
- Electrical gremlins

ML Training Value: MODERATE - Poor connection vs dead battery
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 11. TRANSMISSION TESTS (If Automatic) 🔄

### 11.1 Transmission Sensor Tests \[E\]

#### Test 11.1.1: ATF Temperature Sensor Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes
Expected Codes: P0710, P0711

Procedure:
1. Baseline scan
2. Disconnect ATF temp sensor
3. Drive vehicle (if safe)
4. Capture scan
5. Reconnect

Expected Behavior:
- Fixed ATF temp reading
- May affect shift quality
- Transmission may not lock converter

ML Training Value: MODERATE - Transmission-specific fault
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 12. CAN BUS & NETWORK TESTS 🔌

### 12.1 CAN Bus Manipulation \[S\]

#### Test 12.1.1: CAN Message Injection 🟡

```
Risk: MODERATE - Requires CAN interface
Duration: Variable
Expected Codes: Various, depending on injection

Equipment Needed:
- CAN interface (ELM327, CANable, Kvaser)
- python-can library
- Vehicle CAN bus access (OBD-II pins 6 & 14)

Procedure:
1. Baseline scan
2. Monitor CAN traffic, identify target messages
3. Inject fake messages:
   - Fake coolant temp (300°F)
   - Fake speed (100 mph at standstill)
   - Fake RPM values
4. Capture ECU response
5. Stop injection, verify restoration

Expected Behavior:
- ECU may accept or reject fake data
- Cross-checks between sensors may trigger codes
- Limp mode if values are impossible

ML Training Value: VERY HIGH - Network attack detection
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 12.1.2: CAN Bus Flooding \[S\] 🔴

```
Risk: HIGH - Can lock up ECU
Duration: 5-10 seconds MAX
Expected Codes: Various communication codes

Procedure:
1. Baseline scan
2. Flood CAN bus with high-priority messages
3. Overwhelm bus bandwidth
4. Monitor ECU response
5. Stop flooding immediately

Expected Behavior:
- ECU unable to process messages
- Possible limp mode
- Communication errors
- May require ECU reset

ML Training Value: HIGH - DOS attack detection
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 12.1.3: Fault Code Injection via CAN \[S\] 🟢

```
Risk: LOW
Duration: 1-2 minutes
Expected Codes: Injected codes

Procedure:
1. Baseline scan
2. Use CAN tool to write DTC to ECU memory
3. Scan vehicle to see injected code
4. Compare ML model response
5. Clear codes

Expected Behavior:
- Code appears in ECU without actual fault
- ML model should detect inconsistency
  (code present but no parameter anomalies)

ML Training Value: VERY HIGH - False positive detection
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 13. ECU MANIPULATION TESTS \[ECU\]

### 13.1 ECU Parameter Adjustments

#### Test 13.1.1: ECU Reset / Clear Adaptations 🟢

```
Risk: LOW
Duration: 5 minutes
Expected Codes: None

Procedure:
1. Baseline scan with learned adaptations
2. Clear ECU adaptations (disconnect battery 10 min)
3. Reconnect, start engine
4. Capture scan showing "fresh" ECU state
5. Drive to relearn

Expected Behavior:
- Fuel trims reset to 0
- Idle relearn required
- Shift points reset (if auto trans)
- Temporary rough running until relearn

ML Training Value: MODERATE - Identify relearn patterns
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 13.1.2: ECU Reflash with Modified Parameters 🔴

```
Risk: HIGH - Can brick ECU if done wrong
Duration: 30-60 minutes
Expected Codes: None

⚠️ ADVANCED TEST - Requires ECU tuning knowledge

Procedure:
1. Baseline scan with stock tune
2. Read ECU calibration
3. Modify parameter (e.g., fuel table, timing)
4. Flash modified calibration
5. Scan with modified parameters
6. Restore stock calibration

Expected Behavior:
- Engine runs with modified parameters
- Fuel trims compensate (or don't)
- Performance changes detectable

ML Training Value: HIGH - Detect unauthorized ECU modifications
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 14. MULTI-FAULT SCENARIOS 🚨

### 14.1 Combined Fault Tests

#### Test 14.1.1: MAF + O2 Sensor Disconnect 🟡

```
Risk: MODERATE
Duration: 1-2 minutes
Expected Codes: Multiple

Procedure:
1. Baseline scan
2. Disconnect BOTH MAF and O2 sensor
3. Brief engine run
4. Capture multi-fault scan
5. Reconnect both

Expected Behavior:
- Compounded effects
- ECU very confused (no airflow, no O2 feedback)
- Severe running issues

ML Training Value: HIGH - Multi-fault pattern recognition
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 14.1.2: Vacuum Leak + Injector Disconnect 🔴

```
Risk: HIGH
Duration: 30-60 seconds MAX
Expected Codes: Multiple misfire, lean codes

Procedure:
1. Baseline scan
2. Create vacuum leak + disconnect one injector
3. Very brief test
4. Capture scan
5. Immediately restore

Expected Behavior:
- System-wide lean condition + one cylinder dead
- Complex fault interaction
- ML model must identify both issues

ML Training Value: VERY HIGH - Real-world complexity
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 15. INTERMITTENT FAULT SIMULATION ⚡

### 15.1 Intermittent Connection Tests \[E\]

#### Test 15.1.1: Vibration-Induced Connector Fault 🟡

```
Risk: MODERATE
Duration: 3-5 minutes
Expected Codes: Variable, intermittent

Procedure:
1. Baseline scan
2. Partially disconnect sensor connector (not fully seated)
3. Rev engine, create vibration
4. Connector may make/break contact
5. Capture intermittent fault scan
6. Fully reconnect

Expected Behavior:
- Intermittent signal loss
- Codes may set and clear
- ECU "freezes" last good value
- Hard to diagnose (typical real-world issue)

ML Training Value: VERY HIGH - Intermittent detection crucial
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

#### Test 15.1.2: Temperature-Induced Sensor Failure \[M\] 🟡

```
Risk: MODERATE
Duration: 10-15 minutes
Expected Codes: Variable

Procedure:
1. Cold baseline scan
2. Heat specific sensor with heat gun (carefully)
   - Simulate sensor failing when hot
3. Monitor parameter drift
4. Let cool, verify restoration

Expected Behavior:
- Sensor readings drift with temperature
- Out-of-spec when hot, OK when cold
- Classic intermittent fault pattern

ML Training Value: HIGH - Temperature-dependent failures
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 16. BRAKE SYSTEM TESTS 🛑

### 16.1 ABS Sensor Tests \[E\]

#### Test 16.1.1: Wheel Speed Sensor Disconnect 🟢

```
Risk: LOW
Duration: 2-3 minutes (vehicle stationary)
Expected Codes: C0035, C0040 (wheel speed sensor)

Procedure:
1. Baseline scan
2. Disconnect one wheel speed sensor
3. Key on, attempt to move vehicle slowly
4. ABS warning light should illuminate
5. Capture scan
6. Reconnect

Expected Behavior:
- ABS disabled
- Warning light on
- Wheel speed shows 0 for that wheel
- ABS module throws code

ML Training Value: MODERATE - Brake system specific
Status: ☐ Not Tested | ☐ Complete | Date: ___________
```

---

## 17. CUSTOM / EXPERIMENTAL TESTS 🧪

### 17.1 New Tests (Add Your Discoveries Here!)

#### Test 17.1.1: \[Your Test Name\] \__\_

```
Risk: ___
Duration: ___
Expected Codes: ___

Procedure:
1. ___
2. ___
3. ___

Expected Behavior:
- ___

ML Training Value: ___
Status: ☐ Not Tested | ☐ Complete | Date: ___________
Notes: ___
```

---

## 📊 TEST EXECUTION TRACKER

### Completed Tests by Category:

- Air Intake: ☐☐☐☐ (0/4)
- Oxygen Sensors: ☐☐☐☐ (0/4)
- Throttle/Accel: ☐☐ (0/2)
- Fuel System: ☐☐ (0/2)
- Ignition System: ☐☐ (0/2)
- Cooling System: ☐☐☐ (0/3)
- Vacuum/Pressure: ☐☐☐ (0/3)
- Exhaust/Emissions: ☐☐ (0/2)
- Camshaft/Timing: ☐ (0/1)
- Electrical System: ☐☐ (0/2)
- Transmission: ☐ (0/1)
- CAN Bus: ☐☐☐ (0/3)
- ECU Manipulation: ☐☐ (0/2)
- Multi-Fault: ☐☐ (0/2)
- Intermittent: ☐☐ (0/2)
- Brake System: ☐ (0/1)
- Custom: ☐☐☐ (0/3+)

**Total Tests Defined:** 35+
**Total Tests Completed:** 0
**Completion Rate:** 0%

---

## 🎯 PRIORITY TESTING ORDER (Recommended)

### Phase 1: Safe & Easy (Weeks 1-2)
1. ✅ MAF Disconnect (1.1.1)
2. ✅ O2 Sensor Disconnect B1S1 (2.1.1)
3. ✅ Coolant Temp Sensor Disconnect (6.1.1)
4. ✅ PCV Vacuum Leak (7.1.1)

### Phase 2: Moderate Risk (Weeks 3-4)
5. ✅ IAT Sensor Tests (6.1.3)
6. ✅ Brake Booster Vacuum Leak (7.1.2)
7. ✅ TPS Disconnect (3.1.1)
8. ✅ MAF Contamination (1.1.3)

### Phase 3: Advanced (Month 2)
9. ✅ Single Injector Disconnect (4.1.1) - BRIEF!
10. ✅ Single Coil Disconnect (5.1.1) - BRIEF!
11. ✅ CAN Bus Injection (12.1.1)
12. ✅ Multi-Fault Scenarios (14.1.1)

### Phase 4: Expert Level (Month 3+)
13. ✅ ECU Parameter Modification (13.1.2)
14. ✅ Intermittent Fault Simulation (15.1.1)
15. ✅ CAN Bus Flooding (12.1.2)

---

## 🔬 DATA COLLECTION STANDARDS

### For Every Test:
1. **File Naming Convention:**
   ```
   VEHICLE_DATE_TIME_testID_condition.csv
   Example: TOYOTA_20260113_1430_1.1.1_maf_disconnect.csv
   ```

2. **Required Metadata:**
   - Test ID (from this document)
   - Date/Time
   - Engine temperature (cold/warm/hot)
   - Ambient temperature
   - Pre-test mileage
   - Any unusual conditions

3. **Scan Duration:**
   - Baseline: 3 minutes
   - Fault: 1-3 minutes (depending on risk)
   - Restored: 2 minutes

4. **Documentation:**
   - Photos of setup
   - Notes on observed behavior
   - Any unexpected results
   - Verification of restoration

---

## 📚 SAFETY PROTOCOLS

### Before ANY Test:
- ☐ Read test procedure completely
- ☐ Understand risk level
- ☐ Have reconnection plan ready
- ☐ Fire extinguisher nearby
- ☐ Phone available for emergency
- ☐ Vehicle in safe location
- ☐ Good ventilation

### During Test:
- Monitor engine closely
- Watch for smoke/unusual smells
- Keep test duration minimal
- Be ready to abort immediately
- Document everything

### After Test:
- Verify complete restoration
- Clear codes properly
- Test drive to ensure normal operation
- Document any persistent issues

---

## 🔄 VERSION HISTORY

| Version | Date | Changes | By |
|---------|------|---------|-----|
| 1.0 | 2026-01-13 | Initial creation - 35 tests defined | AI + User |
| ___ | __________ | _________________________________ | ___ |
| ___ | __________ | _________________________________ | ___ |

---

## 💡 IDEAS FOR FUTURE TESTS

**Add ideas here as you think of them:**

1. Knock sensor disconnection (listen for timing retard)
2. Camshaft position sensor (CPS) disconnect
3. Crankshaft position sensor (CKP) - will not start
4. Evaporative emissions purge valve stuck open/closed
5. Secondary air injection pump disconnect
6. Radiator fan disconnect (overheat simulation)
7. Throttle body carbon buildup simulation
8. Fuel pressure drop (partially pinch fuel line?)
9. Exhaust restriction (block tailpipe partially)
10. ___________________________________________
11. ___________________________________________
12. ___________________________________________

---

**This document lives and grows with your testing!**
**Update after every test, add new ideas, refine procedures.**

---

*Remember: Quality data over quantity. One perfect test is worth 100 rushed ones.* 🎯
