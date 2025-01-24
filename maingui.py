from flask import Flask, request, jsonify, render_template
import os
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from dotenv import load_dotenv
import plotly_gauge
from IEC import determine_laser_class
from laserReport import laser_safety_notes
from laserReport import get_safety_notes  # Import the function to get safety notes
from geocal import calculate_laser_class
import geocal
import math


load_dotenv()

app = Flask(__name__, template_folder='templates')

# Set your Mistral API key
api_key = "ktgGKrYBZQz9FlHs26EYxSPtQjOR38CA"
model = "mistral-large-latest"
client = MistralClient(api_key=api_key)

@app.route('/')
def loader():
        return render_template('loader.html')

@app.route('/index')
def index():
    return render_template('mainGui.html')

@app.route('/ask', methods=['POST'])
def ask():
    try:
        print("ask function called")

        data = request.json
        inputs = data.get('inputs', [])
        laser_modes = data.get('laser_modes', [])

        # Construct the prompt from the inputs
        prompt = (
            "imagine you are a laser safety expert and a physics guru versed in calculations relating to lasers. "
            "Use the attached inputs to calculate the laser class and using the AEL classification, show in 200 words or less "
            "if the laser beam is safe for the human eye and skin. In the end state, provide 3 things: 1. class of laser, "
            "2. if safe, write 'it's safe', and if unsafe, write 'it's unsafe'. "
            "Inputs: " + ', '.join(inputs) + ". "
            "Laser Modes: " + ', '.join(laser_modes) + "."
        )

        # Get a response from Mistral AI
        chat_response = client.chat(
            model=model,
            messages=[ChatMessage(role="user", content=prompt)]
        )

        response_text = chat_response.choices[0].message.content

        print("Response generated and sent back")
        return jsonify({'response': response_text})

    except Exception as e:
        error_message = str(e)
        print("Error:", error_message)
        return jsonify({'error': error_message}), 500

@app.route('/generate_gauge_plot', methods=['POST'])
def generate_gauge_plot():
    try:
        data = request.json
        laser_class = data.get('laser_class', 'unknown')

        # Generate the gauge plot
        gauge_plot = plotly_gauge.generate_gauge_plot(laser_class)

        print("Gauge plot created")
        return jsonify({'gauge_plot': gauge_plot})

    except Exception as e:
        error_message = str(e)
        print("Error:", error_message)
        return jsonify({'error': error_message}), 500


#Laser Geometery section
@app.route('/determine_laser_class', methods=['POST'])
def determine_laser_class_route():
    try:
        data = request.json
        wavelength = float(data['wavelength'])
        duration = float(data['duration'])
        power = float(data['power'])
        unit = data['unit']
        print("determine_laser_class function called")
        print(f"data: {data}")
        laser_class = determine_laser_class(wavelength, power, duration, unit)
        print("Laser class determined:", laser_class)  # Debug print

        # Correct the mapping process
        laser_class_key = laser_class.replace("Laser ", "")  # Remove "Laser " prefix if present
        print("Mapped laser class key:", laser_class_key)  # Debug print

        # Retrieve the safety notes from the dictionary
        safety_notes = laser_safety_notes.get(laser_class_key, {
            "Eye Safety": f"No safety notes available for {laser_class}.",
            "Skin Safety": f"No safety notes available for {laser_class}."
        })
        print("Safety notes:", safety_notes)  # Debug print

        return jsonify({
            'laser_class': laser_class,
            'safety_notes': safety_notes
        })

    except Exception as e:
        error_message = str(e)
        print("Error:", error_message)
        return jsonify({'error': error_message}), 500


@app.route('/calculate-laser-class', methods=['POST'])
def calculate_laser_class_endpoint():
    try:
        # Extracting data from the POST request
        data = request.json
        print("Received data:", data)  # Debug print

        # Validate required parameters
        required_params = ['P', 'wavelength', 'tau', 'D0', 'theta', 'D_aperture', 'z']
        for param in required_params:
            if param not in data:
                return jsonify({"error": f"Missing parameter: {param}"}), 400
            if data[param] is None or not isinstance(data[param], (int, float)) or data[param] <= 0:
                return jsonify({"error": f"Invalid value for {param}: {data[param]}. Must be a positive number."}), 400

        # Extract parameters
        P = float(data['P'])
        wavelength = float(data['wavelength'])
        tau = float(data['tau'])
        D0 = float(data['D0'])
        theta = float(data['theta'])
        D_aperture = float(data['D_aperture'])
        z = float(data['z'])

        print(f"Parsed parameters: P={P}, wavelength={wavelength}, tau={tau}, D0={D0}, theta={theta}, D_aperture={D_aperture}, z={z}")  # Debug print

        # Step 1: Calculate values using geocal.py
        calculated_values = geocal.calculate_laser_class(P, wavelength, tau, D0, theta, D_aperture, z)
        if calculated_values is None:
            return jsonify({"error": "Calculation failed."}), 500

        print("Calculated values:", calculated_values)  # Debug print

        # Step 2: Compare with AEL and get the laser class
        laser_class = geocal.list_and_compare_ael(calculated_values)
        if laser_class is None:
            return jsonify({"error": "AEL comparison failed."}), 500

        print("Laser class:", laser_class)  # Debug print

        # Correct the mapping process
        laser_class_key = laser_class.replace("Laser ", "")  # Remove "Laser " prefix if present
        print("Mapped laser class key:", laser_class_key)  # Debug print

        # Retrieve the safety notes from the dictionary in laserReport.py
        safety_notes = get_safety_notes(laser_class_key)
        print("Safety notes:", safety_notes)  # Debug print

        return jsonify({
            'calculated_values': calculated_values,
            'laser_class': laser_class,
            'safety_notes': safety_notes
        })

    except Exception as e:
        error_message = str(e)
        print("Error:", error_message)
        return jsonify({'error': error_message}), 500

if __name__ == '__main__':
    app.run(debug=True, port=50001)