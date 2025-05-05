from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import OpenAI
import docx


# Initialize the Flask app
app = Flask(__name__)
CORS(app)

# Starte nettside:
# cd "C:\Users\sebls\OneDrive - NLA Høgskolen\Skole NLA\Master\NettsideV3"
# python app.py

# Set your OpenAI API key
client = OpenAI(
    api_key = os.environ.get("OPENAI_API_KEY")
)

# Henter ut teksten i word, pdf og json. Gjør det om til strings.
# Function to extract text from a Word document
def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        return str(e)

# Route to upload and process a docx file containing profiles
@app.route("/upload_profiles", methods=["POST"])
def upload_profiles():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

# Save the uploaded file
    file_path = os.path.join("uploads", file.filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(file_path)

# Extract text from the uploaded docx file
    extracted_text = extract_text_from_docx(file_path)

    # Return the extracted text as confirmation
    return jsonify({"message": "Profiles uploaded successfully", "extracted_text": extracted_text})


# Route for handling GPT requests
@app.route("/api/gpt", methods=["POST"])
def gpt_response():
    try:
        # Get text data from JSON request
        data = request.get_json()
        prompt = data.get("prompt")
        profiles_text = data.get("profiles_text")

        # Validate input
        if not prompt or not profiles_text:
            return jsonify({"error": "Missing prompt or profiles text in request"}), 400

        # Make a request to the GPT API
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        r"""
Formål: Generere realistiske matematikkoppgaver basert på elevprofilene som er oppgitt.
Disse elevprofilene beskriver elevenes interesser, hva de vil bli når de vil bli store og deres favorittfag. Bruk denne informasjonen som utgangspunkt når oppgavene genereres.

Dette er et eksempel på en matematikkoppgave som er passende for en 12 år gammel elev:
"Å leie en bysykkel i 60 min koster 29 kr. Hvis du leier sykkelen i mer enn 60 min, koster det 15 kr ekstra per påbegynte kvarter.
Leier du en bysykkel i for eksempel 61 min, må du betale 29 kr pluss 15 kr, altså 44 kr til sammen. Nora har leid en bysykkel i 95 min. Hvor mye må Nora betale"

De følgende kriteriene og retningslinjene skal ikke nevnes i oppgaven som genereres. 
Oppgavene som genereres skal vurderes opp mot et rammeverk som tar utgangspunkt i de følgende 7 kriteriene. Generer oppgaver som oppfyller disse kriteriene.
1. Situasjon: Oppgaven må handle om en realistisk situasjon fra en 12-årings hverdag, basert på deres interesser og aktiviteter.
2. Spørsmål: Spørsmålet skal være praktisk og nyttig i situasjonen, for eksempel å beregne tid, kostnader eller mengder.
3. Eksistens av informasjon: All nødvendig informasjon må være lett tilgjengelig og kjent for en 12-åring, som priser eller vanlige tidsbruk.
4. Realisme: Tall og fakta må samsvare med virkeligheten. Bruk omtrentlige verdier der presisjon ikke er naturlig eller nødvendig.
5. Løsningsstrategi: Oppgaven må gi rom for ulike metoder og strategier for å finne svaret.
6. Krav til løsning: Løsningen skal være realistisk og logisk, uten unødvendige forenklinger.
7. Formål: Oppgaven må ha et klart formål som eleven kan se nytteverdien i å løse.

Følgende retningslinjer må også følges når oppgavene skal genereres. Dette er for at oppgavene skal være tilpasset elevgruppen som skal arbeide med oppgavene.
- Oppgaven skrives på norsk. 
- Oppgaven består av mellom 3 og 5 deloppgaver.
- Oppgavens vanskelighetsgrad blir progressivt vanskeligere.                      
- Oppgaven skal ikke inneholde egennavn.
- Formuleringen til oppgaven skal være kort og presis.
- Oppgaven skal være utfordrende for en gjennomsnittlig 7. trinns elev (12 år) å løse.                                                   
                        """
                    )
                },
                {"role": "user", "content": f"Profiles: {profiles_text}\nPrompt: {prompt}"}
            ],
        )
        # Get the text response from GPT
        gpt_text = response.choices[0].message.content.strip()

# Send the generated task back to GPT for evaluation
        evaluation_response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        r"""
Formål: Forbedre den gitte oppgaven. Den nye oppgaven skal være forbedret basert på følgende 6 kriterier:
- Oppgaven bruker enkelt og tydelig språk som er lett å forstå for 7. trinns elever.
- Formuleringen i oppgaven skal være kort og presis.
- Oppgaven skal ikke inneholde hint.
- Der det ikke er behov for definitive verdier bruker oppgaven begreper som "omtrent" og "cirka" istedenfor.
- Oppgaven skal være realistisk.
- Oppgaven skal bli progressivt vanskeligere.
- Oppgaven inneholder ikke tekstformatering.
                        """
                    )
                },
                {"role": "user", "content": f"Oppgave: {gpt_text}"}
            ],
        )

        # Get the evaluation text 
        evaluation_text = evaluation_response.choices[0].message.content.strip()

        # Return both the generated task and its evaluation
        return jsonify({"generated_task": gpt_text, "evaluation": evaluation_text})


    except Exception as e:
        return jsonify({"error": str(e)})
       
# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
