from flask import Blueprint, jsonify, request
import json
import uuid
from werkzeug.utils import secure_filename
import os

data_analysis_bp = Blueprint("data_analysis", __name__)

# Configure upload settings
UPLOAD_FOLDER = ".tmp/uploads"
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json", "txt"}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@data_analysis_bp.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_extension = filename.rsplit(".", 1)[1].lower()
        saved_filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        
        file.save(file_path)
        
        # Mock analysis for demo
        analysis = {
            "summary": {
                "rows": 100,
                "columns": 5,
                "missing_values": 2,
                "data_types": {
                    "Name": "text",
                    "Age": "number",
                    "Salary": "number",
                    "Department": "text",
                    "Experience": "number"
                }
            },
            "columns": {
                "Name": {"type": "text", "missing": 0, "unique_values": 100},
                "Age": {"type": "number", "missing": 1, "unique_values": 45, "min": 22, "max": 65, "mean": 35.5, "std": 12.3},
                "Salary": {"type": "number", "missing": 0, "unique_values": 87, "min": 35000, "max": 120000, "mean": 67500, "std": 18500},
                "Department": {"type": "text", "missing": 0, "unique_values": 4},
                "Experience": {"type": "number", "missing": 1, "unique_values": 25, "min": 0, "max": 40, "mean": 8.2, "std": 7.1}
            },
            "suggested_charts": [
                {"type": "scatter", "title": "Age vs Salary", "x_column": "Age", "y_column": "Salary"},
                {"type": "histogram", "title": "Distribution of Age", "column": "Age"},
                {"type": "bar", "title": "Count by Department", "column": "Department"},
                {"type": "box", "title": "Salary by Department", "x_column": "Department", "y_column": "Salary"},
                {"type": "correlation_heatmap", "title": "Correlation Heatmap", "columns": ["Age", "Salary", "Experience"]},
                {"type": "line", "title": "Line Chart: Age vs Salary", "x_column": "Age", "y_column": "Salary"},
                {"type": "area", "title": "Area Chart: Age vs Salary", "x_column": "Age", "y_column": "Salary"},
                {"type": "pie", "title": "Proportion by Department", "column": "Department"}
            ],
            "insights": [
                "Dataset contains 3 numeric columns suitable for statistical analysis.",
                "Dataset contains 2 categorical columns for grouping and segmentation.",
                "Dataset has 2 missing values that may need attention.",
                "Strong correlation expected between Age, Experience, and Salary."
            ]
        }
        
        return jsonify({
            "file_id": file_id,
            "filename": filename,
            "analysis": analysis
        })
    
    return jsonify({"error": "Invalid file type"}), 400

@data_analysis_bp.route("/generate-chart", methods=["POST"])
def generate_chart():
    data = request.json
    file_id = data.get("file_id")
    chart_config = data.get("chart_config")
    
    if not file_id or not chart_config:
        return jsonify({"error": "Missing file_id or chart_config"}), 400
    
    # Mock chart data for demo
    mock_chart_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" # A 1x1 transparent PNG base64
    
    return jsonify({"chart_image_base64": mock_chart_base64})

@data_analysis_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    file_id = data.get("file_id")
    
    # Simple AI-like responses
    response = "I\"m here to help you analyze your data! "
    
    if "correlation" in message.lower():
        response += "Based on your data, I can see potential correlations between Age, Experience, and Salary. Older employees with more experience tend to have higher salaries."
    elif "distribution" in message.lower():
        response += "The age distribution in your dataset appears to be fairly normal, with most employees between 30-50 years old."
    elif "trend" in message.lower():
        response += "There\"s a clear upward trend in salary as both age and experience increase. This suggests a positive correlation between these variables."
    elif "summary" in message.lower() or "overview" in message.lower():
        response += "Your dataset contains 100 employees across 4 departments. The average salary is $67,500 with ages ranging from 22 to 65 years."
    else:
        response += "You can ask me about correlations, distributions, trends, or request a summary of your data. I\"ll provide insights based on the uploaded dataset."
    
    return jsonify({"response": response})




