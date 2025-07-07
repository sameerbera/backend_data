from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
import os
import pandas as pd
import numpy as np
import json
import uuid
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import io
import base64

data_analysis_bp = Blueprint(\'data_analysis\', __name__)

# Configure upload settings
UPLOAD_FOLDER = \'/tmp/uploads\'
ALLOWED_EXTENSIONS = {\'csv\', \'xlsx\', \'xls\', \'json\'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return \'.\' in filename and filename.rsplit(\'\', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_data(df):
    """Analyze the uploaded data and suggest appropriate visualizations"""
    analysis = {
        \'summary\': {},
        \'columns\': {},
        \'suggested_charts\': [],
        \'insights\': []
    }
    
    # Basic summary
    analysis[\'summary\'] = {
        \'rows\': int(len(df)),
        \'columns\': int(len(df.columns)),
        \'missing_values\': int(df.isnull().sum().sum()),
        \'data_types\': df.dtypes.astype(str).to_dict()
    }
    
    # Column analysis
    for col in df.columns:
        col_info = {
            \'type\': str(df[col].dtype),
            \'missing\': int(df[col].isnull().sum()),
            \'unique_values\': int(df[col].nunique())
        }
        
        if df[col].dtype in [\'int64\', \'float64\']:
            col_info.update({
                \'min\': float(df[col].min()) if not pd.isna(df[col].min()) else None,
                \'max\': float(df[col].max()) if not pd.isna(df[col].max()) else None,
                \'mean\': float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                \'std\': float(df[col].std()) if not pd.isna(df[col].std()) else None
            })
        
        analysis[\'columns\'][col] = col_info
    
    # Suggest charts based on data characteristics
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=[\'object\']).columns.tolist()
    
    if len(numeric_cols) >= 2:
        analysis[\'suggested_charts\'].append({
            \'type\': \'scatter\',
            \'title\': f\'Scatter Plot: {numeric_cols[0]} vs {numeric_cols[1]}\',
            \'x_column\': numeric_cols[0],
            \'y_column\': numeric_cols[1]
        })
        
        analysis[\'suggested_charts\'].append({
            \'type\': \'correlation_heatmap\',
            \'title\': \'Correlation Heatmap\',
            \'columns\': numeric_cols
        })

        # Line chart for first two numeric columns if suitable
        analysis[\'suggested_charts\'].append({
            \'type\': \'line\',
            \'title\': f\'Line Plot: {numeric_cols[0]} vs {numeric_cols[1]}\',
            \'x_column\': numeric_cols[0],
            \'y_column\': numeric_cols[1]
        })

        # Area chart for first two numeric columns if suitable
        analysis[\'suggested_charts\'].append({
            \'type\': \'area\',
            \'title\': f\'Area Plot: {numeric_cols[0]} vs {numeric_cols[1]}\',
            \'x_column\': numeric_cols[0],
            \'y_column\': numeric_cols[1]
        })
    
    if len(numeric_cols) >= 1:
        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            analysis[\'suggested_charts\'].append({
                \'type\': \'histogram\',
                \'title\': f\'Distribution of {col}\',
                \'column\': col
            })
    
    if len(categorical_cols) >= 1:
        for col in categorical_cols[:2]:  # Limit to first 2 categorical columns
            if df[col].nunique() <= 20:  # Only for columns with reasonable number of categories
                analysis[\'suggested_charts\'].append({
                    \'type\': \'bar\',
                    \'title\': f\'Count by {col}\',
                    \'column\': col
                })
        # Pie chart for first categorical column if suitable
        if df[categorical_cols[0]].nunique() <= 10: # Limit to 10 categories for pie chart
            analysis[\'suggested_charts\'].append({
                \'type\': \'pie\',
                \'title\': f\'Proportion by {categorical_cols[0]}\',
                \'column\': categorical_cols[0]
            })
    
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        analysis[\'suggested_charts\'].append({
            \'type\': \'box\',
            \'title\': f\'{numeric_cols[0]} by {categorical_cols[0]}\',
            \'x_column\': categorical_cols[0],
            \'y_column\': numeric_cols[0]
        })
    
    # Generate insights
    if len(numeric_cols) > 0:
        analysis[\'insights\'].append(f"Dataset contains {len(numeric_cols)} numeric columns suitable for statistical analysis.")
    
    if len(categorical_cols) > 0:
        analysis[\'insights\'].append(f"Dataset contains {len(categorical_cols)} categorical columns for grouping and segmentation.")
    
    if analysis[\'summary\'][\'missing_values\'] > 0:
        analysis[\'insights\'].append(f"Dataset has {analysis[\'summary\'][\'missing_values\']} missing values that may need attention.")
    
    return analysis

def generate_chart(df, chart_config):
    """Generate a chart based on the configuration"""
    chart_type = chart_config[\'type\']
    
    # Define a modern template and color palette
    template = \'plotly_white\'
    color_discrete_sequence = px.colors.qualitative.Plotly # A good default palette

    try:
        if chart_type == \'scatter\':
            fig = px.scatter(df, x=chart_config[\'x_column\'], y=chart_config[\'y_column\'], 
                           title=chart_config[\'title\'], template=template, 
                           color_discrete_sequence=color_discrete_sequence)
        
        elif chart_type == \'histogram\':
            fig = px.histogram(df, x=chart_config[\'column\'], title=chart_config[\'title\'], 
                             template=template, color_discrete_sequence=color_discrete_sequence)
        
        elif chart_type == \'bar\':
            value_counts = df[chart_config[\'column\']].value_counts()
            fig = px.bar(x=value_counts.index, y=value_counts.values, 
                        title=chart_config[\'title\'], template=template,
                        labels={\'x\': chart_config[\'column\'], \'y\': \'Count\'}, 
                        color_discrete_sequence=color_discrete_sequence)
        
        elif chart_type == \'box\':
            fig = px.box(df, x=chart_config[\'x_column\'], y=chart_config[\'y_column\'], 
                        title=chart_config[\'title\'], template=template, 
                        color_discrete_sequence=color_discrete_sequence)
        
        elif chart_type == \'correlation_heatmap\':
            numeric_df = df[chart_config[\'columns\']].select_dtypes(include=[np.number])
            corr_matrix = numeric_df.corr()
            fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", 
                          title=chart_config[\'title\'], template=template,
                          color_continuous_scale=px.colors.sequential.Viridis) # Use a sequential color scale for heatmaps
        
        elif chart_type == \'line\':
            fig = px.line(df, x=chart_config[\'x_column\'], y=chart_config[\'y_column\'], 
                          title=chart_config[\'title\'], template=template, 
                          color_discrete_sequence=color_discrete_sequence)

        elif chart_type == \'area\':
            fig = px.area(df, x=chart_config[\'x_column\'], y=chart_config[\'y_column\'], 
                          title=chart_config[\'title\'], template=template, 
                          color_discrete_sequence=color_discrete_sequence)

        elif chart_type == \'pie\':
            value_counts = df[chart_config[\'column\']].value_counts()
            fig = px.pie(names=value_counts.index, values=value_counts.values, 
                         title=chart_config[\'title\'], template=template, 
                         color_discrete_sequence=color_discrete_sequence)
        
        else:
            return None
        
        # Convert to JSON
        fig_json = json.dumps(fig, cls=PlotlyJSONEncoder)
        return fig_json
    
    except Exception as e:
        print(f"Error generating chart: {e}")
        return None

@data_analysis_bp.route(\'/upload\', methods=[\'POST\'])
def upload_file():
    if \'file\' not in request.files:
        return jsonify({\'error\': \'No file provided\'}), 400
    
    file = request.files[\'file\']
    if file.filename == \'\':
        return jsonify({\'error\': \'No file selected\'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_extension = filename.rsplit(\'\', 1)[1].lower()
        saved_filename = f\"{file_id}.{file_extension}\"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        
        file.save(file_path)
        
        try:
            # Load the data
            if file_extension == \'csv\':
                df = pd.read_csv(file_path)
            elif file_extension in [\'xlsx\', \'xls\']:
                df = pd.read_excel(file_path)
            elif file_extension == \'json\':
                df = pd.read_json(file_path)
            
            # Perform analysis
            analysis = analyze_data(df)
            
            # Store analysis results (in a real app, you\'d use a database)
            analysis_path = os.path.join(UPLOAD_FOLDER, f\"{file_id}_analysis.json\")
            with open(analysis_path, \'w\') as f:
                json.dump(analysis, f)
            
            return jsonify({
                \'file_id\': file_id,
                \'filename\': filename,
                \'analysis\': analysis
            })
        
        except Exception as e:
            return jsonify({\'error\': f\'Error processing file: {str(e)}\'}), 500
    
    return jsonify({\'error\': \'Invalid file type\'}), 400

@data_analysis_bp.route(\'/generate-chart\', methods=[\'POST\'])
def generate_chart_endpoint():
    data = request.json
    file_id = data.get(\'file_id\')
    chart_config = data.get(\'chart_config\')
    
    if not file_id or not chart_config:
        return jsonify({\'error\': \'Missing file_id or chart_config\'}), 400
    
    try:
        # Find the data file
        data_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id) and not f.endswith(\'_analysis.json\')]
        if not data_files:
            return jsonify({\'error\': \'Data file not found\'}), 404
        
        data_file = data_files[0]
        file_path = os.path.join(UPLOAD_FOLDER, data_file)
        file_extension = data_file.split(\'.\')[-1]
        
        # Load the data
        if file_extension == \'csv\':
            df = pd.read_csv(file_path)
        elif file_extension in [\'xlsx\', \'xls\']:
            df = pd.read_excel(file_path)
        elif file_extension == \'json\':
            df = pd.read_json(file_path)
        
        # Generate chart
        chart_json = generate_chart(df, chart_config)
        
        if chart_json:
            return jsonify({\'chart\': chart_json})
        else:
            return jsonify({\'error\': \'Failed to generate chart\'}), 500
    
    except Exception as e:
        return jsonify({\'error\': f\'Error generating chart: {str(e)}\'}), 500

@data_analysis_bp.route(\'/chat\', methods=[\'POST\'])
def chat():
    data = request.json
    message = data.get(\'message\', \'\')
    file_id = data.get(\'file_id\')
    
    # Simple AI-like responses based on keywords
    response = "I\'m here to help you analyze your data! "
    
    if \'correlation\' in message.lower():
        response += "I can show you correlations between numeric variables in your dataset. Try generating a correlation heatmap!"
    elif \'distribution\' in message.lower():
        response += "To see data distributions, I recommend creating histograms for your numeric columns."
    elif \'trend\' in message.lower():
        response += "For trends over time, line charts work best if you have time-series data."
    elif \'compare\' in message.lower():
        response += "For comparisons, bar charts or box plots are great depending on your data type."
    elif \'summary\' in message.lower() or \'overview\' in message.lower():
        if file_id:
            try:
                analysis_path = os.path.join(UPLOAD_FOLDER, f\"{file_id}_analysis.json\")
                if os.path.exists(analysis_path):
                    with open(analysis_path, \'r\') as f:
                        analysis = json.load(f)
                    response += f"Your dataset has {analysis[\'summary\'][\'rows\']} rows and {analysis[\'summary\'][\'columns\']} columns. "
                    if analysis[\'summary\'][\'missing_values\'] > 0:
                        response += f"There are {analysis[\'summary\'][\'missing_values\']} missing values. "
                    response += "I\'ve suggested some charts that would work well with your data!"
            except:
                pass
    else:
        response += "You can ask me about correlations, distributions, trends, comparisons, or request a summary of your data."
    
    return jsonify({\'response\': response})



