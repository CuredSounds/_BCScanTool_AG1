# LAUNCH X431 PRO3 V+ Elite - Tacoma Diagnostic Guide

## 🎯 Quick Start Guide

Your LAUNCH X431 doesn't work with standard OBD-II Python libraries because it uses proprietary protocols. Here's how to diagnose your Tacoma's head gasket:

---

## 📱 Method 1: Use LAUNCH Scanner Directly (RECOMMENDED)

### Step 1: Run Diagnosis on Scanner
1. **Power on** the LAUNCH X431 tablet
2. **Connect** SmartlinkC 2.0 VCI to Tacoma OBD-II port
3. **Turn ignition ON**
4. **Launch the app** on the tablet
5. **Select**: Toyota → Tacoma → 2011 → 4.0L V6

### Step 2: Monitor Live Data
Monitor these key parameters for 10 minutes:
- **Coolant Temperature** (should stay 195-220°F)
- **Long Term Fuel Trim Bank 1** (should be ±10%)
- **Long Term Fuel Trim Bank 2** (should be ±10%)
- **O2 Sensor Bank 1 Sensor 1**
- **O2 Sensor Bank 2 Sensor 1**
- **Engine Load**
- **RPM**

### Step 3: Export Data
1. While viewing live data, look for **"Save"** or **"Export"** button
2. Save as CSV or Excel file
3. Transfer file to your MacBook via:
   - Email
   - USB drive
   - Cloud storage (Dropbox, Google Drive)
   - Direct USB connection

### Step 4: Analyze with Python
```bash
cd /Users/sonic.design/tacoma_diagnostics
source venv/bin/activate
python analyze_launch_export.py tacoma_data.csv
```

---

## 🔍 Method 2: Manual Diagnosis on Scanner

### Head Gasket Indicators to Look For:

#### 🌡️ **Temperature Issues:**
- ✅ Normal: 195-220°F steady
- ⚠️  Warning: 221-230°F
- 🔴 Fail: >230°F or fluctuating ±10°F

#### ⛽ **Fuel Trim Issues:**
- ✅ Normal: -10% to +10%
- ⚠️  Warning: -15% to -10% or +10% to +15%
- 🔴 Fail: <-15% or >+15%

#### 💨 **Misfires:**
- ✅ Normal: 0 misfires
- ⚠️  Warning: Occasional misfires
- 🔴 Fail: Consistent misfires on same cylinder

#### 🌊 **O2 Sensor Behavior:**
- ✅ Normal: Fluctuating 0.1V - 0.9V
- ⚠️  Warning: Stuck lean (<0.3V) or rich (>0.7V)
- 🔴 Fail: No fluctuation

---

## 🛠️ Method 3: Buy ELM327 WiFi Adapter

If you want to use Python scripts directly, get an ELM327 WiFi adapter:

### Recommended Adapters:
1. **OBDLink MX+ WiFi** ($80) - Best quality, most reliable
2. **VGATE iCar WiFi** ($30) - Good mid-range option
3. **Generic ELM327 WiFi** ($20) - Budget option

### Setup:
1. Plug adapter into OBD-II port
2. Connect MacBook to adapter's WiFi network
3. Run: `python _BCScanTool1.py`

---

## 📊 What to Do with Results

### If Analysis Shows Head Gasket Failure:

**Immediate Actions:**
1. ❌ **Don't drive** if overheating
2. 📞 **Get quotes** from mechanics ($2,200-3,700)
3. 🔧 **DIY option**: $600-1,000 parts + 20-30 hours

**Mechanical Tests to Confirm:**
1. Chemical combustion gas test (blue fluid test)
2. Compression test (all 6 cylinders)
3. Leak-down test
4. Cooling system pressure test
5. Visual inspection for external leaks

### If Analysis is Inconclusive:
- Get mechanical tests done anyway
- Monitor symptoms:
  - White smoke from exhaust
  - Sweet smell from vents
  - Oil milky/foamy
  - Coolant loss
  - Rough idle

---

## 💡 Tips for Best Results

1. **Start with cold engine** if possible
2. **Let idle for 10 minutes** during data logging
3. **Watch for patterns** not just single readings
4. **Document everything** for mechanic
5. **Save multiple sessions** to track changes

---

## 🆘 Troubleshooting

**Scanner won't connect:**
- Check VCI is plugged into OBD-II port
- Verify ignition is ON
- Try restarting scanner
- Check for blown fuses in Tacoma

**Can't find export option:**
- Check scanner manual
- Look under "Data Logger" or "Live Data"
- Try "Report" or "History" menus
- Some models auto-save to internal storage

**Data file won't load:**
- Ensure file is CSV or Excel format
- Check file isn't corrupted
- Try opening in Excel first to verify

---

## 📞 Need Help?

Created by: Brent Chadwell (Neural Harmonics Lab)
Date: October 23, 2025
Vehicle: 2011 Toyota Tacoma SR5 4.0L V6
Scanner: LAUNCH X431 PRO3 V+ Elite with SmartlinkC 2.0

