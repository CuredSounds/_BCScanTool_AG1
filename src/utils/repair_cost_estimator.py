"""
Repair Cost Estimation Module
Estimates repair costs based on diagnosed issues
"""

import pandas as pd
from typing import Dict, List


class RepairCostEstimator:
    """
    Estimates repair costs for common vehicle issues
    """

    # Average repair costs (labor + parts) in USD
    REPAIR_COSTS = {
        # Ignition System
        'spark_plugs': {'min': 100, 'max': 300, 'typical': 150, 'labor_hours': 1.0},
        'ignition_coil': {'min': 150, 'max': 400, 'typical': 250, 'labor_hours': 1.5},
        'ignition_coil_set': {'min': 400, 'max': 1200, 'typical': 700, 'labor_hours': 3.0},

        # Fuel System
        'fuel_injector': {'min': 200, 'max': 600, 'typical': 350, 'labor_hours': 2.0},
        'fuel_injector_cleaning': {'min': 80, 'max': 150, 'typical': 100, 'labor_hours': 0.5},
        'fuel_pump': {'min': 400, 'max': 1200, 'typical': 700, 'labor_hours': 2.5},
        'fuel_filter': {'min': 50, 'max': 150, 'typical': 80, 'labor_hours': 0.5},

        # Oxygen Sensors
        'o2_sensor': {'min': 150, 'max': 400, 'typical': 200, 'labor_hours': 1.0},

        # Cooling System
        'thermostat': {'min': 150, 'max': 350, 'typical': 200, 'labor_hours': 1.5},
        'coolant_flush': {'min': 100, 'max': 200, 'typical': 130, 'labor_hours': 1.0},
        'water_pump': {'min': 300, 'max': 750, 'typical': 450, 'labor_hours': 2.5},
        'radiator': {'min': 400, 'max': 1200, 'typical': 700, 'labor_hours': 3.0},

        # Emissions
        'catalytic_converter': {'min': 800, 'max': 2500, 'typical': 1400, 'labor_hours': 2.0},

        # Air Intake
        'maf_sensor': {'min': 150, 'max': 400, 'typical': 250, 'labor_hours': 0.5},
        'air_filter': {'min': 20, 'max': 60, 'typical': 35, 'labor_hours': 0.25},
        'vacuum_leak_repair': {'min': 100, 'max': 500, 'typical': 250, 'labor_hours': 1.5},

        # Engine
        'compression_test': {'min': 100, 'max': 200, 'typical': 150, 'labor_hours': 1.0},
        'valve_adjustment': {'min': 150, 'max': 400, 'typical': 250, 'labor_hours': 2.0},
        'head_gasket': {'min': 1200, 'max': 3000, 'typical': 1800, 'labor_hours': 8.0},

        # Diagnostic
        'diagnostic_scan': {'min': 80, 'max': 150, 'typical': 100, 'labor_hours': 0.5},
    }

    # Issue to repair mapping
    ISSUE_TO_REPAIR = {
        # Cylinder-specific misfire
        'single_cylinder_misfire': [
            ('spark_plugs', 0.85, 'Start here - most common cause'),
            ('ignition_coil', 0.90, 'If spark plugs don\'t fix it'),
            ('fuel_injector', 0.70, 'Less common but possible'),
            ('compression_test', 1.0, 'Verify no mechanical issues'),
        ],

        # Multiple cylinder misfire
        'multiple_cylinder_misfire': [
            ('fuel_pump', 0.75, 'Affects all cylinders'),
            ('maf_sensor', 0.70, 'Air/fuel mixture issue'),
            ('vacuum_leak_repair', 0.65, 'Lean condition'),
            ('spark_plugs', 0.80, 'Wear affects multiple'),
        ],

        # Oxygen sensor
        'o2_sensor_failure': [
            ('o2_sensor', 0.95, 'Direct replacement'),
        ],

        # Cooling issues
        'overheating': [
            ('thermostat', 0.70, 'Most common cause'),
            ('coolant_flush', 0.60, 'Low coolant or air'),
            ('water_pump', 0.50, 'Circulation failure'),
            ('radiator', 0.40, 'Clogged or leaking'),
        ],

        'running_cold': [
            ('thermostat', 0.90, 'Stuck open'),
        ],

        # Fuel trim
        'lean_condition': [
            ('vacuum_leak_repair', 0.75, 'Unmetered air'),
            ('maf_sensor', 0.65, 'Incorrect air reading'),
            ('fuel_filter', 0.50, 'Restricted fuel flow'),
            ('fuel_pump', 0.45, 'Weak fuel pressure'),
        ],

        'rich_condition': [
            ('o2_sensor', 0.70, 'Faulty reading'),
            ('maf_sensor', 0.65, 'Incorrect air reading'),
            ('fuel_injector_cleaning', 0.60, 'Leaking injectors'),
        ],

        # Catalytic converter
        'catalyst_damage': [
            ('catalytic_converter', 0.85, 'Replacement needed'),
        ],
    }

    def __init__(self):
        """Initialize repair cost estimator"""
        self.labor_rate = 100  # $/hour

    def set_labor_rate(self, rate: float):
        """Set shop labor rate"""
        self.labor_rate = rate

    def get_repair_cost(self, repair_type: str) -> Dict:
        """
        Get cost estimate for a specific repair

        Args:
            repair_type: Type of repair

        Returns:
            Cost breakdown
        """
        if repair_type not in self.REPAIR_COSTS:
            return {'error': 'Unknown repair type'}

        cost_data = self.REPAIR_COSTS[repair_type]

        return {
            'repair': repair_type,
            'parts_min': cost_data['min'] * 0.6,  # Rough estimate: 60% parts
            'parts_max': cost_data['max'] * 0.6,
            'labor_hours': cost_data['labor_hours'],
            'labor_cost': cost_data['labor_hours'] * self.labor_rate,
            'total_min': cost_data['min'],
            'total_max': cost_data['max'],
            'total_typical': cost_data['typical']
        }

    def estimate_issue_cost(self, issue_type: str) -> List[Dict]:
        """
        Estimate costs for resolving a specific issue

        Args:
            issue_type: Type of issue (e.g., 'single_cylinder_misfire')

        Returns:
            List of possible repairs with costs
        """
        if issue_type not in self.ISSUE_TO_REPAIR:
            return []

        repairs = []
        for repair, probability, note in self.ISSUE_TO_REPAIR[issue_type]:
            cost = self.get_repair_cost(repair)
            if 'error' not in cost:
                cost['probability'] = probability
                cost['note'] = note
                repairs.append(cost)

        return repairs

    def estimate_from_diagnostic(self, diagnostic_results: List[Dict]) -> Dict:
        """
        Estimate total costs from diagnostic results

        Args:
            diagnostic_results: List of detected issues

        Returns:
            Cost estimation summary
        """
        total_min = 0
        total_max = 0
        total_typical = 0
        repair_breakdown = []

        for issue in diagnostic_results:
            issue_category = self._categorize_issue(issue)

            if issue_category:
                repairs = self.estimate_issue_cost(issue_category)

                if repairs:
                    # Take highest probability repair
                    best_repair = max(repairs, key=lambda x: x['probability'])

                    repair_breakdown.append({
                        'issue': issue.get('issue', 'Unknown'),
                        'severity': issue.get('severity', 'UNKNOWN'),
                        'recommended_repair': best_repair['repair'],
                        'probability': best_repair['probability'],
                        'cost_min': best_repair['total_min'],
                        'cost_max': best_repair['total_max'],
                        'cost_typical': best_repair['total_typical'],
                        'note': best_repair['note']
                    })

                    total_min += best_repair['total_min']
                    total_max += best_repair['total_max']
                    total_typical += best_repair['total_typical']

        return {
            'total_min': total_min,
            'total_max': total_max,
            'total_typical': total_typical,
            'repair_breakdown': repair_breakdown
        }

    def _categorize_issue(self, issue: Dict) -> str:
        """Categorize issue for cost estimation"""
        issue_text = issue.get('issue', '').lower()

        if 'cylinder' in issue_text and 'misfire' in issue_text:
            if 'multiple' in issue_text or 'cylinders' in issue_text:
                return 'multiple_cylinder_misfire'
            else:
                return 'single_cylinder_misfire'

        if 'o2' in issue_text or 'oxygen' in issue_text:
            return 'o2_sensor_failure'

        if 'overheating' in issue_text or 'high.*temp' in issue_text:
            return 'overheating'

        if 'cold' in issue_text and 'temp' in issue_text:
            return 'running_cold'

        if 'lean' in issue_text:
            return 'lean_condition'

        if 'rich' in issue_text:
            return 'rich_condition'

        if 'catalyst' in issue_text or 'converter' in issue_text:
            return 'catalyst_damage'

        return None

    def generate_estimate_report(self, diagnostic_results: List[Dict]):
        """Generate formatted cost estimate report"""
        print("\n" + "="*70)
        print("REPAIR COST ESTIMATION")
        print("="*70)

        estimate = self.estimate_from_diagnostic(diagnostic_results)

        if not estimate['repair_breakdown']:
            print("\nNo cost estimates available for detected issues")
            return

        print(f"\nEstimated Total Cost: ${estimate['total_typical']:,.0f}")
        print(f"Range: ${estimate['total_min']:,.0f} - ${estimate['total_max']:,.0f}")

        print("\nRecommended Repairs:")
        for i, repair in enumerate(estimate['repair_breakdown'], 1):
            severity_icon = {'CRITICAL': '🔴', 'WARNING': '⚠️', 'INFO': 'ℹ️'}.get(repair['severity'], '•')

            print(f"\n{i}. {severity_icon} {repair['issue']}")
            print(f"   Recommended: {repair['recommended_repair'].replace('_', ' ').title()}")
            print(f"   Cost: ${repair['cost_typical']:,.0f} (${repair['cost_min']:,.0f} - ${repair['cost_max']:,.0f})")
            print(f"   Probability: {repair['probability']*100:.0f}%")
            print(f"   Note: {repair['note']}")

        print("\n" + "="*70)
        print(f"Labor Rate: ${self.labor_rate}/hour")
        print("Note: Costs are estimates and may vary by location and shop")
        print("="*70)

        return estimate


def estimate_repair_costs(diagnostic_issues: List[Dict], labor_rate=100):
    """
    Main entry point for cost estimation

    Args:
        diagnostic_issues: List of diagnostic issues
        labor_rate: Shop labor rate per hour

    Returns:
        Cost estimation summary
    """
    estimator = RepairCostEstimator()
    estimator.set_labor_rate(labor_rate)

    estimate = estimator.generate_estimate_report(diagnostic_issues)

    return estimate
