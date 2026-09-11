from flask import Flask, request, jsonify, render_template_string
import random
from flask import Flask, request, jsonify, render_template_string
import os
import json
app = Flask(__name__)
import requests



# ============================================================
# MOCK AI RESULTS
# Later, replace this function with real vision AI.
# ============================================================

MOCK_RESULTS = [
    {
        "condition": "Healthy",
        "ripeness": "Ripe",
        "issues": [],
        "severity": 0,
        "recommendation": "No significant visible issues detected.",
        "confidence": 0.94
    },
    {
        "condition": "Unripe",
        "ripeness": "Mostly green",
        "issues": [
            "Peel remains predominantly green"
        ],
        "severity": 1,
        "recommendation": "Allow the banana to ripen before eating.",
        "confidence": 0.91
    },
    {
        "condition": "Overripe",
        "ripeness": "Very ripe",
        "issues": [
            "Extensive brown spotting",
            "Significant peel darkening"
        ],
        "severity": 3,
        "recommendation": "Eat soon or use for cooking.",
        "confidence": 0.94
    },
    {
        "condition": "Possible spoilage",
        "ripeness": "Very ripe",
        "issues": [
            "Severe dark discoloration",
            "Possible mold-like growth"
        ],
        "severity": 4,
        "recommendation": "Do not eat if spoilage or mold is suspected.",
        "confidence": 0.87
    }
]


LEVELS = {
    0: {
        "name": "ALL CLEAR",
        "description": "Healthy-looking banana",
        "class": "level-0"
    },
    1: {
        "name": "LOW CONCERN",
        "description": "Minor banana concerns detected",
        "class": "level-1"
    },
    2: {
        "name": "BANANA ALERT",
        "description": "Noticeable banana issues detected",
        "class": "level-2"
    },
    3: {
        "name": "SERIOUS BANANA EMERGENCY",
        "description": "Significant banana deterioration detected",
        "class": "level-3"
    },
    4: {
        "name": "CRITICAL BANANA EMERGENCY",
        "description": "Severe visible deterioration detected",
        "class": "level-4"
    }
}


# ============================================================
# MAIN PAGE
# ============================================================

@app.route("/")
def home():
    return render_template_string(HTML)


# ============================================================
# MOCK ANALYSIS API
# ============================================================

@app.route("/analyze", methods=["POST"])
@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image submitted."}), 400

    uploaded_file = request.files["image"]

    if uploaded_file.filename == "":
        return jsonify({"error": "No image selected."}), 400

    try:
        # Read the uploaded image
        image_bytes = uploaded_file.read()

        # Convert image to base64
        import base64

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Detect the image type
        content_type = uploaded_file.content_type or "image/jpeg"

        image_data_url = f"data:{content_type};base64,{image_base64}"

        prompt = """
You are the AI inspection system for the
"Banana Emergency Hotline".

Analyze the uploaded image carefully.

Your job is to determine whether the image contains a banana.

If it IS a banana, inspect ONLY what can reasonably
be observed visually.

Do NOT invent spots, damage, mold, bruising,
or discoloration that cannot be seen.

Determine:

1. condition
2. ripeness
3. visible issues
4. emergency severity
5. recommended action
6. confidence

Severity levels:

LEVEL 0 — ALL CLEAR
Healthy-looking banana with no significant visible issues.

LEVEL 1 — LOW CONCERN
Mostly unripe or minor cosmetic issues.

LEVEL 2 — BANANA ALERT
Ripe banana with noticeable but non-severe spots,
bruising, or discoloration.

LEVEL 3 — SERIOUS BANANA EMERGENCY
Very ripe, heavily bruised, significantly damaged,
or substantially deteriorated-looking banana.

LEVEL 4 — CRITICAL BANANA EMERGENCY
Severe visible deterioration or possible mold/spoilage.
Recommend caution.

Return ONLY valid JSON.

Use exactly this structure:

{
    "condition": "Healthy",
    "ripeness": "Ripe",
    "issues": [],
    "severity": 0,
    "recommendation": "No significant visible issues detected.",
    "confidence": 0.94
}

Rules:

- "issues" must be an array.
- "severity" must be an integer from 0 to 4.
- "confidence" must be a number between 0 and 1.
- Do not include markdown.
- Do not include ```json.
- Return JSON only.

If the image is NOT a banana, return:

{
    "condition": "Not a banana",
    "ripeness": "N/A",
    "issues": [],
    "severity": 0,
    "recommendation": "Please submit a clear photo of a banana.",
    "confidence": 0.99
}
"""

        # Send image + prompt to OpenRouter
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openrouter/free",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_url
                                }
                            }
                        ]
                    }
                ]
            },
            timeout=60
        )

        # Show API error in terminal if something goes wrong
        if response.status_code != 200:
            print("OpenRouter error:")
            print(response.status_code)
            print(response.text)

            return jsonify({
                "error": "OpenRouter analysis failed.",
                "details": response.text
            }), 500

        data = response.json()

        # Get AI response
        text = data["choices"][0]["message"]["content"].strip()

        # Remove markdown fences just in case
        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        # Convert AI JSON into Python dictionary
        result = json.loads(text)

        # Make sure severity is valid
        severity = int(result.get("severity", 0))
        severity = max(0, min(4, severity))

        result["severity"] = severity

        # Add our UI level information
        result["level_name"] = LEVELS[severity]["name"]
        result["level_description"] = LEVELS[severity]["description"]
        result["level_class"] = LEVELS[severity]["class"]

        return jsonify(result)

    except json.JSONDecodeError:
        print("AI returned invalid JSON:")
        print(text)

        return jsonify({
            "error": "AI returned an invalid result."
        }), 500

    except Exception as error:
        print("OpenRouter error:")
        print(error)

        return jsonify({
            "error": "OpenRouter analysis failed.",
            "details": str(error)
        }), 500


# ============================================================
# HTML + CSS + JAVASCRIPT
# ============================================================

HTML = """
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Banana Emergency Hotline</title>


    <style>

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }


        body {
            font-family:
                Arial,
                Helvetica,
                sans-serif;

            background: #f7f7f5;
            color: #111;

            min-height: 100vh;
        }


        /* =====================================================
           HEADER
           ===================================================== */

        header {
            height: 72px;

            background: #111;

            color: white;

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 0 6%;

            border-bottom: 4px solid #ffd600;
        }


        .logo {
            font-weight: 900;
            font-size: 18px;
            letter-spacing: 1px;
        }


        .hotline-status {
            font-size: 12px;
            color: #bdbdbd;

            display: flex;
            align-items: center;
            gap: 8px;
        }


        .status-dot {
            width: 8px;
            height: 8px;

            background: #35c759;

            border-radius: 50%;
        }


        /* =====================================================
           GENERAL
           ===================================================== */

        .screen {
            display: none;

            min-height:
                calc(100vh - 72px);

            padding: 60px 20px;
        }


        .screen.active {
            display: flex;

            align-items: center;
            justify-content: center;
        }


        .container {
            width: 100%;
            max-width: 900px;

            margin: auto;
        }


        /* =====================================================
           LANDING
           ===================================================== */

        .landing {
            text-align: center;

            max-width: 800px;

            margin: auto;
        }


        .emergency-label {
            display: inline-block;

            background: #111;
            color: #ffd600;

            font-size: 12px;
            font-weight: 800;

            padding: 8px 14px;

            border-radius: 999px;

            letter-spacing: 1.5px;

            margin-bottom: 24px;
        }


        .landing h1 {
            font-size: clamp(42px, 8vw, 82px);

            line-height: 0.95;

            font-weight: 950;

            letter-spacing: -3px;

            margin-bottom: 24px;
        }


        .landing h1 span {
            color: #e21b23;
        }


        .landing-subtitle {
            font-size: 22px;

            font-weight: 600;

            margin-bottom: 12px;
        }


        .landing-description {
            color: #666;

            font-size: 16px;

            margin-bottom: 36px;
        }


        .primary-button {
            border: none;

            background: #ffd600;

            color: #111;

            padding: 18px 30px;

            border-radius: 12px;

            font-size: 17px;

            font-weight: 900;

            cursor: pointer;

            box-shadow:
                0 5px 0 #111;

            transition: 0.15s;
        }


        .primary-button:hover {
            transform: translateY(-2px);

            box-shadow:
                0 7px 0 #111;
        }


        .primary-button:active {
            transform: translateY(3px);

            box-shadow:
                0 2px 0 #111;
        }


        .disclaimer {
            margin-top: 30px;

            font-size: 12px;

            color: #888;

            max-width: 500px;

            margin-left: auto;
            margin-right: auto;

            line-height: 1.5;
        }


        /* =====================================================
           UPLOAD
           ===================================================== */

        .section-header {
            margin-bottom: 30px;
        }


        .section-header h2 {
            font-size: clamp(32px, 5vw, 52px);

            font-weight: 950;

            letter-spacing: -2px;

            margin-bottom: 10px;
        }


        .section-header p {
            color: #666;

            font-size: 17px;
        }


        .upload-card {
            background: white;

            border: 2px dashed #bbb;

            border-radius: 20px;

            padding: 60px 30px;

            text-align: center;

            cursor: pointer;

            transition: 0.2s;
        }


        .upload-card:hover,
        .upload-card.dragging {
            border-color: #111;

            background: #fffde8;
        }


        .upload-icon {
            font-size: 48px;

            margin-bottom: 15px;
        }


        .upload-title {
            font-size: 20px;

            font-weight: 900;

            margin-bottom: 8px;
        }


        .upload-subtitle {
            color: #888;

            font-size: 14px;
        }


        #fileInput {
            display: none;
        }


        .preview-container {
            display: none;

            margin-top: 25px;

            background: white;

            padding: 20px;

            border-radius: 20px;

            box-shadow:
                0 8px 30px rgba(0,0,0,0.08);
        }


        .preview-container.show {
            display: block;
        }


        .preview-image {
            width: 100%;

            max-height: 450px;

            object-fit: contain;

            border-radius: 12px;

            background: #f3f3f3;
        }


        .file-info {
            display: flex;

            justify-content: space-between;

            align-items: center;

            margin-top: 15px;

            gap: 15px;
        }


        .filename {
            font-weight: 700;

            overflow: hidden;

            text-overflow: ellipsis;

            white-space: nowrap;
        }


        .remove-button {
            background: none;

            border: none;

            color: #d71920;

            font-weight: 800;

            cursor: pointer;
        }


        .analyze-button {
            width: 100%;

            margin-top: 20px;

            border: none;

            background: #111;

            color: white;

            padding: 18px;

            border-radius: 12px;

            font-size: 16px;

            font-weight: 900;

            cursor: pointer;
        }


        .analyze-button:disabled {
            opacity: 0.4;

            cursor: not-allowed;
        }


        /* =====================================================
           LOADING
           ===================================================== */

        .loading-card {
            text-align: center;

            max-width: 600px;

            margin: auto;
        }


        .loading-image {
            width: 260px;

            height: 260px;

            object-fit: cover;

            border-radius: 20px;

            margin-bottom: 35px;

            box-shadow:
                0 10px 40px rgba(0,0,0,0.15);
        }


        .loading-card h2 {
            font-size: 30px;

            font-weight: 950;

            margin-bottom: 25px;
        }


        .spinner {
            width: 45px;

            height: 45px;

            border: 5px solid #ddd;

            border-top-color: #111;

            border-radius: 50%;

            animation: spin 0.8s linear infinite;

            margin: 0 auto 25px;
        }


        @keyframes spin {

            to {
                transform: rotate(360deg);
            }

        }


        .loading-message {
            color: #666;

            font-size: 16px;

            min-height: 24px;
        }


        /* =====================================================
           RESULTS
           ===================================================== */

        .result-container {
            max-width: 850px;

            margin: auto;
        }


        .result-top {
            margin-bottom: 30px;
        }


        .result-top h2 {
            font-size: clamp(30px, 5vw, 48px);

            font-weight: 950;

            letter-spacing: -2px;

            margin-bottom: 20px;
        }


        .result-card {
            background: white;

            border-radius: 24px;

            overflow: hidden;

            box-shadow:
                0 10px 40px rgba(0,0,0,0.1);
        }


        .severity-banner {
            padding: 35px;

            color: white;

            text-align: center;
        }


        .severity-level {
            font-size: 56px;

            font-weight: 950;

            letter-spacing: -2px;
        }


        .severity-name {
            font-size: 18px;

            font-weight: 900;

            letter-spacing: 1px;

            margin-top: 5px;
        }


        /* Severity colors */

        .level-0 {
            background: #2e7d32;
        }


        .level-1 {
            background: #827717;
        }


        .level-2 {
            background: #ef8f00;
        }


        .level-3 {
            background: #d71920;
        }


        .level-4 {
            background: #8b0000;
        }


        .result-body {
            padding: 35px;
        }


        .result-image {
            width: 100%;

            max-height: 400px;

            object-fit: contain;

            border-radius: 15px;

            background: #f3f3f3;

            margin-bottom: 30px;
        }


        .report-grid {
            display: grid;

            grid-template-columns:
                repeat(2, 1fr);

            gap: 18px;
        }


        .report-item {
            background: #f7f7f5;

            padding: 22px;

            border-radius: 15px;
        }


        .report-item.full {
            grid-column: 1 / -1;
        }


        .report-label {
            color: #888;

            font-size: 11px;

            font-weight: 900;

            letter-spacing: 1.2px;

            margin-bottom: 8px;
        }


        .report-value {
            font-size: 19px;

            font-weight: 800;

            line-height: 1.4;
        }


        .issues {
            list-style: none;

            margin-top: 5px;
        }


        .issues li {
            margin-bottom: 8px;

            font-size: 16px;
        }


        .issues li::before {
            content: "•";

            font-weight: 900;

            margin-right: 8px;

            color: #d71920;
        }


        .confidence {
            display: flex;

            justify-content: space-between;

            align-items: center;
        }


        .confidence-number {
            font-size: 26px;

            font-weight: 950;
        }


        .result-note {
            color: #888;

            font-size: 12px;

            line-height: 1.5;

            margin-top: 25px;

            text-align: center;
        }


        .another-button {
            width: 100%;

            margin-top: 25px;

            border: 2px solid #111;

            background: white;

            color: #111;

            padding: 17px;

            border-radius: 12px;

            font-size: 16px;

            font-weight: 900;

            cursor: pointer;
        }


        .another-button:hover {
            background: #111;

            color: white;
        }


        /* =====================================================
           MOBILE
           ===================================================== */

        @media (max-width: 650px) {

            header {
                padding: 0 20px;
            }


            .hotline-status {
                display: none;
            }


            .screen {
                padding: 40px 16px;
            }


            .landing h1 {
                letter-spacing: -2px;
            }


            .upload-card {
                padding: 45px 20px;
            }


            .report-grid {
                grid-template-columns: 1fr;
            }


            .report-item.full {
                grid-column: auto;
            }


            .result-body {
                padding: 20px;
            }


            .severity-banner {
                padding: 28px 20px;
            }


            .severity-level {
                font-size: 46px;
            }

        }

    </style>

</head>


<body>


<header>

    <div class="logo">
        🍌 BEH
    </div>

    <div class="hotline-status">

        <span class="status-dot"></span>

        BANANA HOTLINE ONLINE

    </div>

</header>


<!-- ========================================================
     SCREEN 1
     ======================================================== -->

<section id="landingScreen" class="screen active">

    <div class="landing">

        <div class="emergency-label">
            EMERGENCY BANANA SERVICES
        </div>


        <h1>
            🍌 BANANA<br>
            <span>EMERGENCY</span><br>
            HOTLINE
        </h1>


        <p class="landing-subtitle">
            Because some banana situations cannot wait.
        </p>


        <p class="landing-description">
            AI-powered banana condition assessment
        </p>


        <button
            class="primary-button"
            onclick="showUpload()">

            🚨 INSPECT MY BANANA

        </button>


        <p class="disclaimer">

            For entertainment purposes.
            Banana assessments are based on
            visible characteristics only.

        </p>

    </div>

</section>


<!-- ========================================================
     SCREEN 2
     ======================================================== -->

<section id="uploadScreen" class="screen">

    <div class="container">

        <div class="section-header">

            <h2>
                SUBMIT BANANA EVIDENCE
            </h2>

            <p>
                Upload a clear photo of the banana for inspection.
            </p>

        </div>


        <div
            id="uploadArea"
            class="upload-card"
            onclick="openFilePicker()">

            <div class="upload-icon">
                📸
            </div>

            <div class="upload-title">
                Drop your banana photo here
            </div>

            <div class="upload-subtitle">
                or click to browse
            </div>

        </div>


        <input
            id="fileInput"
            type="file"
            accept="image/*"
            onchange="handleFile(this.files[0])">


        <div
            id="previewContainer"
            class="preview-container">

            <img
                id="previewImage"
                class="preview-image">


            <div class="file-info">

                <div
                    id="filename"
                    class="filename">
                </div>


                <button
                    class="remove-button"
                    onclick="removeImage(event)">

                    REMOVE

                </button>

            </div>


            <button
                id="analyzeButton"
                class="analyze-button"
                disabled
                onclick="analyzeBanana()">

                🔍 ANALYZE BANANA

            </button>

        </div>

    </div>

</section>


<!-- ========================================================
     SCREEN 3
     ======================================================== -->

<section id="loadingScreen" class="screen">

    <div class="loading-card">

        <img
            id="loadingImage"
            class="loading-image">


        <h2>
            BANANA INSPECTION IN PROGRESS
        </h2>


        <div class="spinner"></div>


        <div
            id="loadingMessage"
            class="loading-message">

            Detecting banana condition...

        </div>

    </div>

</section>


<!-- ========================================================
     SCREEN 4
     ======================================================== -->

<section id="resultScreen" class="screen">

    <div class="result-container">

        <div class="result-top">

            <h2>
                🚨 BANANA EMERGENCY ASSESSMENT
            </h2>

        </div>


        <div class="result-card">


            <div
                id="severityBanner"
                class="severity-banner">

                <div
                    id="severityLevel"
                    class="severity-level">

                    LEVEL 3

                </div>


                <div
                    id="severityName"
                    class="severity-name">

                    SERIOUS BANANA EMERGENCY

                </div>

            </div>


            <div class="result-body">


                <img
                    id="resultImage"
                    class="result-image">


                <div class="report-grid">


                    <!-- CONDITION -->

                    <div class="report-item">

                        <div class="report-label">
                            CONDITION
                        </div>

                        <div
                            id="condition"
                            class="report-value">

                            Overripe

                        </div>

                    </div>


                    <!-- RIPENESS -->

                    <div class="report-item">

                        <div class="report-label">
                            RIPENESS
                        </div>

                        <div
                            id="ripeness"
                            class="report-value">

                            Very ripe

                        </div>

                    </div>


                    <!-- ISSUES -->

                    <div class="report-item full">

                        <div class="report-label">
                            VISIBLE ISSUES
                        </div>

                        <ul
                            id="issues"
                            class="issues">
                        </ul>

                    </div>


                    <!-- RECOMMENDATION -->

                    <div class="report-item full">

                        <div class="report-label">
                            RECOMMENDED ACTION
                        </div>

                        <div
                            id="recommendation"
                            class="report-value">

                        </div>

                    </div>


                    <!-- CONFIDENCE -->

                    <div class="report-item full">

                        <div class="report-label">
                            INSPECTION CONFIDENCE
                        </div>

                        <div class="confidence">

                            <span>
                                AI visual assessment
                            </span>

                            <span
                                id="confidence"
                                class="confidence-number">

                                94%

                            </span>

                        </div>

                    </div>

                </div>


                <p class="result-note">

                    Assessment is based only on visible
                    characteristics in the submitted image.

                </p>


                <button
                    class="another-button"
                    onclick="inspectAnother()">

                    🔄 INSPECT ANOTHER BANANA

                </button>


            </div>

        </div>

    </div>

</section>


<script>


    // ========================================================
    // STATE
    // ========================================================

    let selectedFile = null;

    let imageData = null;


    // ========================================================
    // SCREEN MANAGEMENT
    // ========================================================

    function showScreen(screenId) {

        document
            .querySelectorAll(".screen")
            .forEach(screen => {

                screen.classList.remove("active");

            });


        document
            .getElementById(screenId)
            .classList.add("active");

    }


    function showUpload() {

        showScreen("uploadScreen");

    }


    // ========================================================
    // FILE PICKER
    // ========================================================

    function openFilePicker() {

        document
            .getElementById("fileInput")
            .click();

    }


    function handleFile(file) {

        if (!file) {
            return;
        }


        if (!file.type.startsWith("image/")) {

            alert("Please select an image file.");

            return;

        }


        selectedFile = file;


        const reader = new FileReader();


        reader.onload = function(event) {

            imageData = event.target.result;


            document
                .getElementById("previewImage")
                .src = imageData;


            document
                .getElementById("loadingImage")
                .src = imageData;


            document
                .getElementById("resultImage")
                .src = imageData;


            document
                .getElementById("filename")
                .textContent = file.name;


            document
                .getElementById("previewContainer")
                .classList.add("show");


            document
                .getElementById("analyzeButton")
                .disabled = false;

        };


        reader.readAsDataURL(file);

    }


    // ========================================================
    // REMOVE IMAGE
    // ========================================================

    function removeImage(event) {

        event.stopPropagation();


        selectedFile = null;

        imageData = null;


        document
            .getElementById("fileInput")
            .value = "";


        document
            .getElementById("previewContainer")
            .classList.remove("show");


        document
            .getElementById("analyzeButton")
            .disabled = true;

    }


    // ========================================================
    // DRAG AND DROP
    // ========================================================

    const uploadArea =
        document.getElementById("uploadArea");


    uploadArea.addEventListener(
        "dragover",
        function(event) {

            event.preventDefault();

            uploadArea.classList.add("dragging");

        }
    );


    uploadArea.addEventListener(
        "dragleave",
        function() {

            uploadArea.classList.remove("dragging");

        }
    );


    uploadArea.addEventListener(
        "drop",
        function(event) {

            event.preventDefault();


            uploadArea.classList.remove("dragging");


            const file =
                event.dataTransfer.files[0];


            handleFile(file);

        }
    );


    // ========================================================
    // ANALYZE
    // ========================================================

    async function analyzeBanana() {

        if (!selectedFile) {
            return;
        }


        showScreen("loadingScreen");


        const messages = [

            "Detecting banana condition...",

            "Analyzing ripeness...",

            "Checking for visible damage...",

            "Inspecting discoloration...",

            "Preparing emergency assessment...",

            "Banana authorities have been notified..."

        ];


        let messageIndex = 0;


        const messageElement =
            document.getElementById("loadingMessage");


        const messageInterval =
            setInterval(function() {

                messageIndex++;


                if (messageIndex < messages.length) {

                    messageElement.textContent =
                        messages[messageIndex];

                }

            }, 600);


        try {

            const formData = new FormData();

            formData.append("image", selectedFile);


            const response =
                await fetch("/analyze", {

                    method: "POST",

                    body: formData

                });


            const result =
                await response.json();


            clearInterval(messageInterval);


            // Small delay so the loading screen
            // feels like an actual inspection.

            setTimeout(function() {

                displayResult(result);

            }, 500);


        } catch (error) {

            clearInterval(messageInterval);


            alert(
                "The banana hotline encountered an error."
            );


            showUpload();

        }

    }


    // ========================================================
    // DISPLAY RESULT
    // ========================================================

    function displayResult(result) {


        const severity =
            result.severity;


        const banner =
            document.getElementById("severityBanner");


        banner.className =
            "severity-banner " +
            result.level_class;


        document
            .getElementById("severityLevel")
            .textContent =
            "LEVEL " + severity;


        document
            .getElementById("severityName")
            .textContent =
            result.level_name;


        document
            .getElementById("condition")
            .textContent =
            result.condition;


        document
            .getElementById("ripeness")
            .textContent =
            result.ripeness;


        document
            .getElementById("recommendation")
            .textContent =
            result.recommendation;


        document
            .getElementById("confidence")
            .textContent =
            Math.round(result.confidence * 100) + "%";


        const issuesElement =
            document.getElementById("issues");


        issuesElement.innerHTML = "";


        if (result.issues.length === 0) {

            const li =
                document.createElement("li");

            li.textContent =
                "No significant visible issues detected.";

            issuesElement.appendChild(li);

        } else {

            result.issues.forEach(function(issue) {

                const li =
                    document.createElement("li");

                li.textContent = issue;

                issuesElement.appendChild(li);

            });

        }


        showScreen("resultScreen");

    }


    // ========================================================
    // INSPECT ANOTHER
    // ========================================================

    function inspectAnother() {

        selectedFile = null;

        imageData = null;


        document
            .getElementById("fileInput")
            .value = "";


        document
            .getElementById("previewContainer")
            .classList.remove("show");


        document
            .getElementById("analyzeButton")
            .disabled = true;


        showScreen("uploadScreen");

    }


</script>


</body>

</html>
"""


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        debug=False,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )