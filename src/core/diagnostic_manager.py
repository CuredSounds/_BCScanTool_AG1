import os
import logging
import pandas as pd
from typing import Optional, Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DiagnosticManager")

class DiagnosticManager:
    """
    Unified manager for orchestrating all diagnostic and predictive analysis modules.
    Provides a central entry point for the BCScanTool diagnostic suite.
    """

    def __init__(self, sensor_df: pd.DataFrame, report_df: Optional[pd.DataFrame] = None):
        self.sensor_df = sensor_df
        self.report_df = report_df
        self.results = {
            "pid_analysis": None,
            "lstm_analysis": None,
            "autoencoder_analysis": None,
            "diagnostics": None,
            "predictive": None,
            "repair_estimates": None
        }
        self.status = {
            "pid_analysis": "not_started",
            "lstm_analysis": "not_started",
            "autoencoder_analysis": "not_started",
            "diagnostics": "not_started",
            "predictive": "not_started",
            "repair_estimates": "not_started"
        }

    def run_all(self) -> Dict[str, Any]:
        """Run the full diagnostic suite."""
        logger.info("Starting full diagnostic suite...")
        
        self.run_pid_analysis()
        self.run_lstm_analysis()
        self.run_autoencoder_analysis()
        self.run_diagnostics()
        self.run_predictive_analytics()
        self.run_repair_estimates()
        
        logger.info("Full diagnostic suite completed.")
        return self.results

    def run_pid_analysis(self):
        """Run PID-based analysis."""
        try:
            from src.core.pid_analyzer import analyze_pids
            logger.info("Running PID Analysis...")
            analyzer, results, quality = analyze_pids(self.sensor_df)
            self.results["pid_analysis"] = {"results": results, "quality": quality}
            self.status["pid_analysis"] = "success"
        except Exception as e:
            logger.error(f"PID Analysis failed: {e}")
            self.status["pid_analysis"] = f"failed: {str(e)}"

    def run_lstm_analysis(self):
        """Run LSTM time-series prediction analysis."""
        try:
            from src.ml_models.lstm_predictor import run_lstm_analysis
            logger.info("Running LSTM Prediction Analysis...")
            analyzer = run_lstm_analysis(self.sensor_df)
            self.results["lstm_analysis"] = analyzer
            self.status["lstm_analysis"] = "success"
        except Exception as e:
            logger.error(f"LSTM Analysis failed: {e}")
            self.status["lstm_analysis"] = f"failed: {str(e)}"

    def run_autoencoder_analysis(self):
        """Run Autoencoder-based anomaly detection."""
        try:
            from src.ml_models.autoencoder_anomaly import run_autoencoder_analysis
            logger.info("Running Autoencoder Anomaly Detection...")
            results = run_autoencoder_analysis(self.sensor_df)
            self.results["autoencoder_analysis"] = results
            self.status["autoencoder_analysis"] = "success"
        except Exception as e:
            logger.error(f"Autoencoder Analysis failed: {e}")
            self.status["autoencoder_analysis"] = f"failed: {str(e)}"

    def run_diagnostics(self):
        """Run the rules-based diagnostic engine."""
        try:
            from src.core.diagnostic_engine import run_diagnostics
            logger.info("Running Diagnostic Engine...")
            issues = run_diagnostics(self.sensor_df, self.report_df)
            self.results["diagnostics"] = issues
            self.status["diagnostics"] = "success"
        except Exception as e:
            logger.error(f"Diagnostic Engine failed: {e}")
            self.status["diagnostics"] = f"failed: {str(e)}"

    def run_predictive_analytics(self):
        """Run predictive analytics based on scan history."""
        if self.report_df is None or self.report_df.empty:
            logger.warning("Skipping Predictive Analytics: No report data provided.")
            self.status["predictive"] = "skipped: no_report_data"
            return

        try:
            from src.core.predictive_analytics import run_predictive_analytics
            logger.info("Running Predictive Analytics...")
            # Note: run_predictive_analytics typically prints output and saves files
            # but we can capture results if the function is updated to return them.
            results = run_predictive_analytics(self.report_df, self.sensor_df)
            self.results["predictive"] = results
            self.status["predictive"] = "success"
        except Exception as e:
            logger.error(f"Predictive Analytics failed: {e}")
            self.status["predictive"] = f"failed: {str(e)}"

    def run_repair_estimates(self):
        """Generate repair cost estimates based on identified issues."""
        try:
            from src.utils.repair_cost_estimator import estimate_repair_costs
            from src import config
            import csv
            
            diagnostic_file = os.path.join(config.DATA_DIR, 'diagnostic_report.csv')
            if not os.path.exists(diagnostic_file):
                logger.warning("Skipping Repair Estimates: diagnostic_report.csv not found.")
                self.status["repair_estimates"] = "skipped: file_not_found"
                return

            logger.info("Running Repair Cost Estimator...")
            with open(diagnostic_file, 'r') as f:
                reader = csv.DictReader(f)
                issues = list(reader)
                if issues:
                    estimates = estimate_repair_costs(issues, labor_rate=125)
                    self.results["repair_estimates"] = estimates
                    self.status["repair_estimates"] = "success"
                else:
                    self.status["repair_estimates"] = "skipped: no_issues"
        except Exception as e:
            logger.error(f"Repair Cost Estimation failed: {e}")
            self.status["repair_estimates"] = f"failed: {str(e)}"

    def get_summary_report(self) -> str:
        """Generate a text summary of the analysis status and results."""
        summary = ["=== Diagnostic Suite Summary ==="]
        for key, state in self.status.items():
            summary.append(f"{key.replace('_', ' ').title()}: {state}")
        
        if self.results["diagnostics"]:
            summary.append("\nDetected Issues:")
            for issue in self.results["diagnostics"][:5]:  # Show top 5
                summary.append(f"- {issue.get('issue', 'Unknown issue')} ({issue.get('severity', 'info')})")
        
        return "\n".join(summary)
