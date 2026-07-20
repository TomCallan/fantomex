import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[1]))

from fantomex.client import FantomexClient

# A simple fake Plotly figure to log a clean interactive chart
class FakePlotlyFigure:
    def to_json(self):
        import json
        return json.dumps({
            "data": [{
                "x": [1, 2, 3, 4, 5],
                "y": [10, 15, 13, 17, 22],
                "type": "scatter",
                "mode": "lines+markers",
                "marker": { "color": "rgb(37, 99, 235)" }
            }],
            "layout": {
                "title": "Accuracy Trend Over Time",
                "xaxis": { "title": "Epoch" },
                "yaxis": { "title": "Accuracy" }
            }
        })


def main():
    print("Connecting to Fantomex server...")
    with FantomexClient(base_url="http://127.0.0.1:8000") as client:
        # Start a run using our new context manager
        print("Starting run: 'training-session' in project: 'demo-project'...")
        with client.run(
            project_name="demo-project",
            run_name="training-session",
            params={"batch_size": 64, "learning_rate": 0.005, "epochs": 5},
            tags=["demo", "context-manager"]
        ) as run:
            
            # 1. Log metrics over steps
            print("Logging training metrics...")
            for step in range(1, 6):
                loss = 0.5 / step
                acc = 0.7 + (0.2 * (step / 5))
                run.log({"loss": loss, "accuracy": acc}, step=step)
            
            # 2. Log a structured CSV data table
            print("Creating and logging CSV data table...")
            data_file = Path("sample_predictions.csv")
            data_file.write_text("input_text,predicted_label,confidence\n'Hello world','greeting',0.98\n'Buy now','spam',0.92\n'What time is it?','question',0.89")
            
            run.log_file(str(data_file), type="data")
            
            # Clean up local file
            if data_file.exists():
                data_file.unlink()
                
            # 3. Log a plotly interactive plot
            print("Logging interactive Plotly figure...")
            fig = FakePlotlyFigure()
            run.log_plotly(fig, name="accuracy_trend")
            
            print("Run completed successfully!")

if __name__ == "__main__":
    main()
