# Field Test Quick Reference Checklist
**BCScanTool v2.0 - Controlled Fault Testing**

## 🔧 Pre-Test Setup (Do Once)

### Equipment Checklist:
- ☐ Launch X431 PRO3 V+ Elite scanner
- ☐ OBD-II cable
- ☐ Basic hand tools (sockets, wrenches)
- ☐ Flashlight
- ☐ Phone camera for documentation
- ☐ Notebook/clipboard for observations
- ☐ Code reader for clearing DTCs

### Software Setup:
- ☐ Configure standard scan profile on Launch X431
- ☐ Test save location (verify files are being saved)
- ☐ Clear all existing DTCs before starting

### Safety:
- ☐ Vehicle in safe location (driveway/garage)
- ☐ Handbrake engaged
- ☐ Transmission in Park
- ☐ Good ventilation if garage
- ☐ Fire extinguisher nearby

---

## Test 1: MAF Sensor Disconnect ⚡

### Quick Steps:
1. ☐ **Baseline:** Run 3-min normal scan → Save as: `TOYOTA_[DATE]_baseline_maf.csv`
2. ☐ **Locate:** MAF sensor (between air filter & throttle body)
3. ☐ **Disconnect:** Unplug electrical connector
4. ☐ **Start:** Engine running, let stabilize 30 sec
5. ☐ **Scan:** 2-3 minute fault scan → Save as: `TOYOTA_[DATE]_maf_fault.csv`
6. ☐ **Observe:** Note rough idle, CEL, any unusual behavior
7. ☐ **Reconnect:** Plug MAF back in
8. ☐ **Clear:** Clear DTCs
9. ☐ **Verify:** 2-min scan → Save as: `TOYOTA_[DATE]_maf_cleared.csv`

**Label:** `maf_fault`

**Expected Codes:** P0101, P0102, P0171, P0174

---

## Test 2: O2 Sensor Disconnect ⚡

### Quick Steps:
1. ☐ **Baseline:** 3-min normal scan → `TOYOTA_[DATE]_baseline_o2.csv`
2. ☐ **Locate:** Bank 1 Sensor 1 (front O2, before cat)
3. ☐ **Disconnect:** Unplug connector
4. ☐ **Start:** Engine running
5. ☐ **Scan:** 2-3 min → `TOYOTA_[DATE]_o2_fault_b1s1.csv`
6. ☐ **Observe:** CEL, possible rich running
7. ☐ **Reconnect:** Plug O2 back in
8. ☐ **Clear:** DTCs
9. ☐ **Verify:** 2-min scan → `TOYOTA_[DATE]_o2_cleared.csv`

**Label:** `o2_fault_b1s1`

**Expected Codes:** P0131, P0132, P0133

---

## Test 3: Vacuum Leak ⚡

### Quick Steps:
1. ☐ **Baseline:** 3-min scan → `TOYOTA_[DATE]_baseline_vacuum.csv`
2. ☐ **Create leak:** Disconnect PCV valve hose OR brake booster line
   - ⚠️ Small controlled leak only!
3. ☐ **Start:** Engine running
4. ☐ **Scan:** 2-3 min → `TOYOTA_[DATE]_vacuum_leak.csv`
5. ☐ **Observe:** High idle (~1200+ RPM), rough, lean condition
6. ☐ **Reconnect:** Restore vacuum line
7. ☐ **Verify:** 2-min scan → `TOYOTA_[DATE]_vacuum_cleared.csv`

**Label:** `vacuum_leak`

**Expected:** Positive LTFT (+10-25%), possible P0171/P0174

---

## Test 4: Misfire Simulation ⚡

### Quick Steps:
1. ☐ **Baseline:** 3-min scan → `TOYOTA_[DATE]_baseline_misfire.csv`
2. ☐ **Choose method:**
   - Option A: Disconnect Cylinder 1 ignition coil
   - Option B: Disconnect Cylinder 1 fuel injector
3. ☐ **Disconnect:** Chosen component
4. ☐ **Start:** Engine running
5. ☐ **Scan:** 1-2 min MAX → `TOYOTA_[DATE]_misfire_cyl1.csv`
   - ⚠️ BRIEF TEST ONLY - don't let it run long!
6. ☐ **Observe:** Rough idle, flashing CEL, shaking
7. ☐ **IMMEDIATELY Reconnect:** Critical - don't delay
8. ☐ **Clear:** DTCs
9. ☐ **Verify:** 2-min scan → `TOYOTA_[DATE]_misfire_cleared.csv`

**Label:** `misfire_cyl1`

**Expected Codes:** P0300, P0301

---

## Weekly Health Check ⚡

### Quick Protocol:
1. ☐ **Pre-conditions:**
   - Engine fully warmed (195-210°F)
   - All accessories OFF
   - Park, level surface

2. ☐ **Scan phases (5 minutes total):**
   - 0-2 min: Idle
   - 2-3 min: Rev to 2000 RPM, hold
   - 3-4 min: Return to idle
   - 4-5 min: Idle with A/C ON

3. ☐ **Save as:** `TOYOTA_[DATE]_weekly_health.csv`

4. ☐ **Label:** `weekly_baseline`

---

## Post-Test Data Management ⚡

After Each Test:
```bash
# Copy files to proper location
1. ☐ Connect MacBook to scanner/transfer files
2. ☐ Move to appropriate folder:
   data/raw/controlled_faults/[test_type]/
3. ☐ Verify files readable
4. ☐ Update test log with observations
```

---

## Test Log Template 📝

**Test:** _________________
**Date:** _________________
**Time:** _________________
**Temperature:** _________°F
**Engine Temp:** _______°F

**Observations:**
- Before fault: ________________________________
- During fault: ________________________________
- Symptoms: ___________________________________
- DTCs triggered: _____________________________
- After restoration: ___________________________

**Files Saved:**
- Baseline: ___________________________________
- Fault: ______________________________________
- Cleared: ____________________________________

**Photos/Video:** ☐ Yes ☐ No

**Notes:** _______________________________________
_________________________________________________
_________________________________________________

---

## Emergency Procedures ⚠️

**If engine won't start after test:**
1. Double-check all connectors reconnected
2. Verify no vacuum leaks
3. Clear all DTCs
4. Check for blown fuses
5. Let ECU reset (disconnect battery 5 min)

**If engine runs very rough:**
1. Immediately stop test
2. Reconnect all components
3. Clear codes
4. Verify restoration scan shows normal

**If CEL stays on after clearing:**
1. Normal - may need drive cycle to clear
2. Drive gently for 10-20 minutes
3. Re-scan to verify codes gone

---

## Success Criteria ✅

**Good Test:**
- ☐ Clean baseline captured
- ☐ Fault condition clearly different from baseline
- ☐ DTCs match expected codes
- ☐ Restoration verified
- ☐ All files saved correctly
- ☐ Observations documented

**Poor Test (Redo):**
- ☐ Baseline contaminated (engine not warm, etc.)
- ☐ Fault scan too short (<1 minute)
- ☐ Files corrupted/not saved
- ☐ Multiple faults simultaneously
- ☐ Unclear observations

---

## Quick Reference: Sensor Locations

**2011 Toyota Tacoma 4.0L V6:**

- **MAF Sensor:** Intake tube between air filter and throttle body
- **O2 B1S1:** Front exhaust manifold, passenger side, before cat
- **O2 B2S1:** Front exhaust manifold, driver side, before cat
- **PCV Valve:** Top of engine, connects to intake manifold
- **Ignition Coils:** On top of each spark plug (remove engine cover)
- **Fuel Injectors:** Under intake manifold (harder to access)

---

## Test Order Recommendation

**Week 1:** MAF disconnect (easiest, safest)
**Week 2:** Vacuum leak (moderate)
**Week 3:** O2 sensor (requires access to exhaust)
**Week 4:** Misfire (most involved, brief test)

**Don't rush** - one quality test per week is better than all four rushed in one day.

---

## After All Tests Complete ⚡

1. ☐ Retrain ML model with all fault data
2. ☐ Generate updated reports
3. ☐ Validate model accuracy on each fault type
4. ☐ Document detection rates
5. ☐ Plan next round of tests (if needed)

```bash
# Retrain
python python/deep_vehicle_analysis.py

# Generate reports
python python/generate_vehicle_reports.py

# Open and review
open data/reports/*.html
```

---

**Remember:** Safety and data quality over speed! 🛡️

---

*Print this checklist and keep it with your scan tool!*
