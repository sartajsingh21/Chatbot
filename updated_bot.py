import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# To track user states
user_data = {}
problem_counter = 0

# Google Sheets Authentication
def authenticate_google_sheets():
    # Define the scope for Google Sheets and Drive access
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Authenticate using the service account
    creds = ServiceAccountCredentials.from_json_keyfile_name("/Users/sartajsingh/teddybear/google_credentials.json", scope)
    
    # Initialize the client
    client = gspread.authorize(creds)
    
    # Open the sheet by name
    sheet = client.open("Chatbot Sheet").sheet1  # Change "Complaints" to your sheet name
    return sheet

# Register Complaint in Google Sheets
def register_complaint_to_sheet(complaint_data):
    # Authenticate and get the sheet
    sheet = authenticate_google_sheets()
    
    # Prepare the complaint data to insert as a row
    row = [
        complaint_data["complaint_number"],
        complaint_data["name"],
        complaint_data["id_number"],
        complaint_data["mobile_number"],
        complaint_data["problem_type"],
        complaint_data.get("hardware_part", "N/A"),
        complaint_data.get("network_issue", "N/A"),
        str(datetime.datetime.now())
    ]
    
    # Insert the row into the sheet
    sheet.append_row(row)

# Generate Complaint Number
def generate_complaint_number(problem_counter):
    now = datetime.datetime.now()
    yy = now.strftime("%y")
    mm = now.strftime("%m")
    serial = f"{problem_counter:04}"  # Zero-padded to 4 digits
    return f"{yy}{mm}{serial}"

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    global problem_counter
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    response = MessagingResponse()

    if sender not in user_data:
        user_data[sender] = {"step": 1}  # Initialize user's step

    user_state = user_data[sender]

    # Conversation flow
    if user_state["step"] == 1:
        response.message("Register your name")
        user_state["step"] = 2

    elif user_state["step"] == 2:
        user_state["name"] = incoming_msg
        response.message("Tell your ID number")
        user_state["step"] = 3

    elif user_state["step"] == 3:
        user_state["id_number"] = incoming_msg
        response.message("Tell your mobile number")
        user_state["step"] = 4

    elif user_state["step"] == 4:
        user_state["mobile_number"] = incoming_msg
        response.message("What type of problem (hardware or network)?")
        user_state["step"] = 5

    elif user_state["step"] == 5:
        if incoming_msg.lower() in ["hardware", "network"]:
            user_state["problem_type"] = incoming_msg.lower()
            if incoming_msg.lower() == "hardware":
                response.message("Which part? (printer, screen, plotter, or other)")
                user_state["step"] = 6
            else:
                response.message("Is it a single website or multiple websites?")
                user_state["step"] = 7
        else:
            response.message("Please reply with 'hardware' or 'network'.")

    elif user_state["step"] == 6:
        user_state["hardware_part"] = incoming_msg
        problem_counter += 1
        complaint_number = generate_complaint_number(problem_counter)

        # Register complaint in Google Sheets
        complaint_data = {
            "complaint_number": complaint_number,
            "name": user_state["name"],
            "id_number": user_state["id_number"],
            "mobile_number": user_state["mobile_number"],
            "problem_type": user_state["problem_type"],
            "hardware_part": user_state["hardware_part"]
        }
        register_complaint_to_sheet(complaint_data)

        response.message(f"Your complaint is registered. Complaint number: {complaint_number}")
        del user_data[sender]  # End conversation

    elif user_state["step"] == 7:
        user_state["network_issue"] = incoming_msg
        problem_counter += 1
        complaint_number = generate_complaint_number(problem_counter)

        # Register complaint in Google Sheets
        complaint_data = {
            "complaint_number": complaint_number,
            "name": user_state["name"],
            "id_number": user_state["id_number"],
            "mobile_number": user_state["mobile_number"],
            "problem_type": user_state["problem_type"],
            "network_issue": user_state["network_issue"]
        }
        register_complaint_to_sheet(complaint_data)

        response.message(f"Your complaint is registered. Complaint number: {complaint_number}")
        del user_data[sender]  # End conversation

    return str(response)

if __name__ == '__main__':
    app.run(debug=True)